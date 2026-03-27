from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact


TOKEN_UNIT = 10**18
INITIAL_ALLOCATION = 200_000 * TOKEN_UNIT
TIMELOCK_DELAY_SECONDS = 120
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
SUPPORT_FOR = 1


class GovernanceLifecycleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "token": load_artifact("src/governance/CampusInnovationFundToken/CampusInnovationFundToken.json"),
            "governor": load_artifact("src/governance/InnovationGovernor/InnovationGovernor.json"),
            "timelock": load_artifact(
                "lib/openzeppelin-contracts/contracts/governance/TimelockController/TimelockController.json"
            ),
            "target": load_artifact("src/mocks/GovernedActionTarget/GovernedActionTarget.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.deployer = self.w3.eth.accounts[0]
        self.voter_a = self.w3.eth.accounts[1]
        self.voter_b = self.w3.eth.accounts[2]
        self.voter_c = self.w3.eth.accounts[3]
        self.low_power = self.w3.eth.accounts[4]

        self.timelock = self._deploy(
            "timelock",
            [TIMELOCK_DELAY_SECONDS, [], [ZERO_ADDRESS], self.deployer],
        )
        self.token = self._deploy("token", [self.deployer])
        self.governor = self._deploy("governor", [self.token.address, self.timelock.address])
        self.target = self._deploy("target", [self.timelock.address])

        self._send(self.token.functions.mint(self.voter_a, INITIAL_ALLOCATION))
        self._send(self.token.functions.mint(self.voter_b, INITIAL_ALLOCATION))
        self._send(self.token.functions.mint(self.voter_c, INITIAL_ALLOCATION))
        self._send(self.token.functions.mint(self.low_power, 1_000 * TOKEN_UNIT))

        self._send(self.token.functions.delegate(self.voter_a), sender=self.voter_a)
        self._send(self.token.functions.delegate(self.voter_b), sender=self.voter_b)
        self._send(self.token.functions.delegate(self.voter_c), sender=self.voter_c)
        self._send(self.token.functions.delegate(self.low_power), sender=self.low_power)

        proposer_role = self.timelock.functions.PROPOSER_ROLE().call()
        canceller_role = self.timelock.functions.CANCELLER_ROLE().call()
        admin_role = self.timelock.functions.DEFAULT_ADMIN_ROLE().call()
        self._send(self.timelock.functions.grantRole(proposer_role, self.governor.address))
        self._send(self.timelock.functions.grantRole(canceller_role, self.governor.address))
        self._send(self.timelock.functions.renounceRole(admin_role, self.deployer))

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.deployer})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _assert_reverts(self, fn):
        with self.assertRaises(TransactionFailed):
            fn()

    def _mine_blocks(self, count: int) -> None:
        self.eth_tester.mine_blocks(count)

    def _latest_timestamp(self) -> int:
        return self.eth_tester.get_block_by_number("latest")["timestamp"]

    def _proposal_payload(self, new_value: int = 42):
        targets = [self.target.address]
        values = [0]
        calldatas = [self.target.functions.setTrackedValue(new_value)._encode_transaction_data()]
        description = f"Set tracked value to {new_value}"
        description_hash = Web3.keccak(text=description)
        return targets, values, calldatas, description, description_hash

    def _propose_and_succeed(self, new_value: int = 42):
        targets, values, calldatas, description, description_hash = self._proposal_payload(new_value)
        self._send(
            self.governor.functions.propose(targets, values, calldatas, description),
            sender=self.voter_a,
        )
        proposal_id = self.governor.functions.hashProposal(targets, values, calldatas, description_hash).call()
        self._mine_blocks(1)
        self._send(self.governor.functions.castVote(proposal_id, SUPPORT_FOR), sender=self.voter_a)
        self._send(self.governor.functions.castVote(proposal_id, SUPPORT_FOR), sender=self.voter_b)
        self._mine_blocks(21)
        return proposal_id, targets, values, calldatas, description_hash

    def test_low_vote_account_cannot_propose(self):
        targets, values, calldatas, description, _ = self._proposal_payload()
        self._assert_reverts(
            lambda: self.governor.functions.propose(targets, values, calldatas, description).transact(
                {"from": self.low_power}
            )
        )

    def test_governor_lifecycle_executes_via_timelock(self):
        proposal_id, targets, values, calldatas, description_hash = self._propose_and_succeed(42)
        self._send(self.governor.functions.queue(targets, values, calldatas, description_hash), sender=self.voter_a)

        self.eth_tester.time_travel(self._latest_timestamp() + TIMELOCK_DELAY_SECONDS + 1)
        self.eth_tester.mine_blocks(1)
        self._send(self.governor.functions.execute(targets, values, calldatas, description_hash), sender=self.voter_b)

        self.assertEqual(self.target.functions.trackedValue().call(), 42)
        self.assertEqual(self.governor.functions.state(proposal_id).call(), 7)

    def test_queue_reverts_before_proposal_succeeds(self):
        targets, values, calldatas, description, description_hash = self._proposal_payload(43)
        self._send(
            self.governor.functions.propose(targets, values, calldatas, description),
            sender=self.voter_a,
        )
        self._assert_reverts(
            lambda: self.governor.functions.queue(targets, values, calldatas, description_hash).transact(
                {"from": self.voter_a}
            )
        )

    def test_execute_reverts_before_queue(self):
        _, targets, values, calldatas, description_hash = self._propose_and_succeed(44)
        self._assert_reverts(
            lambda: self.governor.functions.execute(targets, values, calldatas, description_hash).transact(
                {"from": self.voter_a}
            )
        )

    def test_execute_reverts_before_timelock_delay_expires(self):
        _, targets, values, calldatas, description_hash = self._propose_and_succeed(45)
        self._send(self.governor.functions.queue(targets, values, calldatas, description_hash), sender=self.voter_a)
        self._assert_reverts(
            lambda: self.governor.functions.execute(targets, values, calldatas, description_hash).transact(
                {"from": self.voter_b}
            )
        )


if __name__ == "__main__":
    unittest.main()