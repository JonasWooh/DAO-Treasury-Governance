from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact


TOKEN_UNIT = 10**18


class ReputationAndHybridVotesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "token": load_artifact("src/governance/CampusInnovationFundToken/CampusInnovationFundToken.json"),
            "reputation": load_artifact("src/governance/ReputationRegistry/ReputationRegistry.json"),
            "hybrid": load_artifact("src/governance/HybridVotesAdapter/HybridVotesAdapter.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.owner = self.w3.eth.accounts[0]
        self.workflow = self.w3.eth.accounts[1]
        self.member = self.w3.eth.accounts[2]

        self.token = self._deploy("token", [self.owner])
        self.reputation = self._deploy("reputation", [self.owner, self.workflow])
        self.hybrid = self._deploy("hybrid", [self.token.address, self.reputation.address])

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.owner})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.owner})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _mine_blocks(self, count: int) -> None:
        self.eth_tester.mine_blocks(count)

    def test_reputation_registry_tracks_activation_history_and_total_active_reputation(self):
        self._send(self.reputation.functions.registerMember(self.member, 100))
        registered_block = self.w3.eth.block_number
        self._mine_blocks(1)

        self.assertEqual(self.reputation.functions.reputationOf(self.member).call(), 100)
        self.assertTrue(self.reputation.functions.isActiveMember(self.member).call())
        self.assertEqual(self.reputation.functions.totalActiveReputation().call(), 100)
        self.assertEqual(self.reputation.functions.getPastReputation(self.member, registered_block).call(), 100)
        self.assertTrue(self.reputation.functions.isActiveAt(self.member, registered_block).call())

        self._send(self.reputation.functions.setMemberActive(self.member, False))
        deactivated_block = self.w3.eth.block_number
        self._mine_blocks(1)

        self.assertFalse(self.reputation.functions.isActiveMember(self.member).call())
        self.assertEqual(self.reputation.functions.totalActiveReputation().call(), 0)
        self.assertFalse(self.reputation.functions.isActiveAt(self.member, deactivated_block).call())

        self._send(self.reputation.functions.applyWorkflowReputationDelta(self.member, -150), sender=self.workflow)
        self.assertEqual(self.reputation.functions.reputationOf(self.member).call(), 0)
        self.assertEqual(self.reputation.functions.totalActiveReputation().call(), 0)

    def test_hybrid_votes_use_active_history_for_current_and_past_snapshots(self):
        self._send(self.token.functions.mint(self.member, 1_000 * TOKEN_UNIT))
        self._send(self.token.functions.delegate(self.member), sender=self.member)
        self._send(self.reputation.functions.registerMember(self.member, 100))

        self.assertEqual(self.hybrid.functions.getVotes(self.member).call(), 1_000 * TOKEN_UNIT)

        active_snapshot_block = self.w3.eth.block_number
        self._mine_blocks(1)

        self._send(self.reputation.functions.setMemberActive(self.member, False))
        self.assertEqual(self.hybrid.functions.getVotes(self.member).call(), 600 * TOKEN_UNIT)

        inactive_snapshot_block = self.w3.eth.block_number
        self._mine_blocks(1)

        self.assertEqual(self.hybrid.functions.getPastVotes(self.member, active_snapshot_block).call(), 1_000 * TOKEN_UNIT)
        self.assertEqual(self.hybrid.functions.getPastVotes(self.member, inactive_snapshot_block).call(), 600 * TOKEN_UNIT)
        self.assertEqual(self.hybrid.functions.getPastTotalSupply(active_snapshot_block).call(), 1_000 * TOKEN_UNIT)


if __name__ == "__main__":
    unittest.main()
