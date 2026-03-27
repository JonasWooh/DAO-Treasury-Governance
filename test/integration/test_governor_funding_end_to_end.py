from __future__ import annotations

import unittest
from typing import Callable

from eth_tester import EthereumTester, PyEVMBackend
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact, predict_create_address


TOKEN_UNIT = 10**18
INITIAL_ALLOCATION = 200_000 * TOKEN_UNIT
TIMELOCK_DELAY_SECONDS = 120
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = b"\x00" * 32
SUPPORT_FOR = 1
WETH = 10**18


class GovernorFundingEndToEndTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "timelock": load_artifact(
                "lib/openzeppelin-contracts/contracts/governance/TimelockController/TimelockController.json"
            ),
            "token": load_artifact("src/governance/CampusInnovationFundToken/CampusInnovationFundToken.json"),
            "reputation": load_artifact("src/governance/ReputationRegistry/ReputationRegistry.json"),
            "hybrid": load_artifact("src/governance/HybridVotesAdapter/HybridVotesAdapter.json"),
            "governor": load_artifact("src/governance/InnovationGovernor/InnovationGovernor.json"),
            "funding": load_artifact("src/funding/FundingRegistry/FundingRegistry.json"),
            "treasury": load_artifact("src/treasury/InnovationTreasury/InnovationTreasury.json"),
            "mock_weth": load_artifact("src/mocks/MockWETH/MockWETH.json"),
            "mock_chainlink": load_artifact("src/mocks/MockChainlinkAggregatorV3/MockChainlinkAggregatorV3.json"),
            "mock_pool": load_artifact("src/mocks/MockAavePool/MockAavePool.json"),
            "mock_a_token": load_artifact("src/mocks/MockAToken/MockAToken.json"),
            "oracle": load_artifact("src/oracle/TreasuryOracle/TreasuryOracle.json"),
            "adapter": load_artifact("src/adapters/AaveWethAdapter/AaveWethAdapter.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.deployer = self.w3.eth.accounts[0]
        self.voter_a = self.w3.eth.accounts[1]
        self.voter_b = self.w3.eth.accounts[2]
        self.voter_c = self.w3.eth.accounts[3]
        self.recipient = self.w3.eth.accounts[4]
        self._salt_counter = 1

        self.timelock = self._deploy(
            "timelock",
            [TIMELOCK_DELAY_SECONDS, [self.deployer], [ZERO_ADDRESS], self.deployer],
        )
        self.token = self._deploy("token", [self.deployer])

        predicted_funding = predict_create_address(self.deployer, self.w3.eth.get_transaction_count(self.deployer) + 3)
        self.reputation = self._deploy("reputation", [self.timelock.address, predicted_funding])
        self.hybrid = self._deploy("hybrid", [self.token.address, self.reputation.address])
        self.governor = self._deploy("governor", [self.hybrid.address, self.timelock.address])
        self.funding = self._deploy("funding", [self.timelock.address, self.governor.address, self.reputation.address])
        self.assertEqual(self.funding.address, predicted_funding)

        self.weth = self._deploy("mock_weth", [])
        self.pool = self._deploy("mock_pool", [self.weth.address])
        self.a_token = self.w3.eth.contract(
            address=self.pool.functions.aToken().call(),
            abi=self.artifacts["mock_a_token"]["abi"],
        )
        self.chainlink = self._deploy("mock_chainlink", [])
        self.oracle = self._deploy("oracle", [self.chainlink.address, 3_600])

        predicted_treasury = predict_create_address(self.deployer, self.w3.eth.get_transaction_count(self.deployer) + 1)
        self.adapter = self._deploy(
            "adapter",
            [predicted_treasury, self.weth.address, self.pool.address, self.a_token.address],
        )
        self.treasury = self._deploy(
            "treasury",
            [self.timelock.address, self.weth.address, self.oracle.address, self.adapter.address, self.funding.address],
        )
        self.assertEqual(self.treasury.address, predicted_treasury)

        self._send(self.chainlink.functions.setRoundData(2_000 * 10**8, self._latest_timestamp(), 8))
        self._send(self.weth.functions.mint(self.treasury.address, 3 * WETH))

        for voter in (self.voter_a, self.voter_b, self.voter_c):
            self._send(self.token.functions.mint(voter, INITIAL_ALLOCATION))
            self._send(self.token.functions.delegate(voter), sender=voter)
            self._execute_via_timelock(self.reputation.functions.registerMember(voter, 100))

        proposer_role = self.timelock.functions.PROPOSER_ROLE().call()
        canceller_role = self.timelock.functions.CANCELLER_ROLE().call()
        self._send(self.timelock.functions.grantRole(proposer_role, self.governor.address))
        self._send(self.timelock.functions.grantRole(canceller_role, self.governor.address))

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.deployer})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _mine_blocks(self, count: int) -> None:
        self.eth_tester.mine_blocks(count)

    def _latest_timestamp(self) -> int:
        return self.eth_tester.get_block_by_number("latest")["timestamp"]

    def _next_salt(self) -> bytes:
        value = self._salt_counter.to_bytes(32, byteorder="big")
        self._salt_counter += 1
        return value

    def _execute_via_timelock(self, call) -> None:
        salt = self._next_salt()
        data = call._encode_transaction_data()
        self._send(self.timelock.functions.schedule(call.address, 0, data, ZERO_BYTES32, salt, TIMELOCK_DELAY_SECONDS))
        self.eth_tester.time_travel(self._latest_timestamp() + TIMELOCK_DELAY_SECONDS + 1)
        self._mine_blocks(1)
        self._send(self.timelock.functions.execute(call.address, 0, data, ZERO_BYTES32, salt))

    def _execute_governor_proposal(
        self,
        *,
        proposer: str,
        voters: list[str],
        targets: list[str],
        values: list[int],
        calldatas: list[bytes],
        description: str,
        after_propose: Callable[[int], None] | None = None,
    ) -> int:
        self._send(self.governor.functions.propose(targets, values, calldatas, description), sender=proposer)
        description_hash = Web3.keccak(text=description)
        proposal_id = self.governor.functions.hashProposal(targets, values, calldatas, description_hash).call()
        if after_propose is not None:
            after_propose(proposal_id)
        self._mine_blocks(1)
        for voter in voters:
            self._send(self.governor.functions.castVote(proposal_id, SUPPORT_FOR), sender=voter)
        self._mine_blocks(21)
        self._send(self.governor.functions.queue(targets, values, calldatas, description_hash), sender=proposer)
        self.eth_tester.time_travel(self._latest_timestamp() + TIMELOCK_DELAY_SECONDS + 1)
        self._mine_blocks(1)
        self._send(self.governor.functions.execute(targets, values, calldatas, description_hash), sender=voters[0])
        self.assertEqual(self.governor.functions.state(proposal_id).call(), 7)
        return proposal_id

    def test_governor_executes_full_v2_workflow_with_treasury_and_reputation(self):
        self._send(
            self.funding.functions.submitProposal(
                "Smart Recycling Kiosk",
                "ipfs://proposal-metadata",
                self.recipient,
                2 * WETH // 10,
                ["Milestone 0", "Milestone 1"],
                [WETH // 10, WETH // 10],
            ),
            sender=self.voter_a,
        )
        funding_proposal_id = int(self.funding.functions.proposalCount().call())
        project_id = self.funding.functions.deriveProjectId(funding_proposal_id, self.voter_a, self.recipient).call()

        proposal1_targets = [self.funding.address, self.treasury.address]
        proposal1_values = [0, 0]
        proposal1_calldatas = [
            self.funding.functions.markProposalApproved(funding_proposal_id, project_id)._encode_transaction_data(),
            self.treasury.functions.approveProject(project_id, self.recipient, 2 * WETH // 10, 2)._encode_transaction_data(),
        ]
        proposal1_id = self._execute_governor_proposal(
            proposer=self.voter_a,
            voters=[self.voter_a, self.voter_b, self.voter_c],
            targets=proposal1_targets,
            values=proposal1_values,
            calldatas=proposal1_calldatas,
            description="Proposal 1: approve funding workflow project",
            after_propose=lambda governor_proposal_id: self._send(
                self.funding.functions.linkGovernorProposal(funding_proposal_id, governor_proposal_id),
                sender=self.voter_a,
            ),
        )

        self._send(
            self.funding.functions.settleVoteParticipationBatch(
                funding_proposal_id,
                [self.voter_a, self.voter_b, self.voter_c],
            ),
            sender=self.voter_b,
        )
        self.assertEqual(self.funding.functions.getProposal(funding_proposal_id).call()[8], proposal1_id)
        self.assertEqual(self.reputation.functions.getMember(self.voter_a).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_c).call()[2], 102)
        self.assertEqual(self.funding.functions.getMilestone(funding_proposal_id, 0).call()[4], 1)
        self.assertEqual(self.funding.functions.getMilestone(funding_proposal_id, 1).call()[4], 0)

        proposal2_targets = [self.treasury.address]
        proposal2_values = [0]
        proposal2_calldatas = [self.treasury.functions.depositIdleFunds(6 * WETH // 10)._encode_transaction_data()]
        self._execute_governor_proposal(
            proposer=self.voter_a,
            voters=[self.voter_a, self.voter_b, self.voter_c],
            targets=proposal2_targets,
            values=proposal2_values,
            calldatas=proposal2_calldatas,
            description="Proposal 2: deposit idle WETH into Aave",
        )

        self.assertEqual(self.treasury.functions.liquidWethBalance().call(), 24 * WETH // 10)
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 6 * WETH // 10)
        self.assertEqual(self.reputation.functions.getMember(self.voter_a).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_c).call()[2], 102)

        self._send(
            self.funding.functions.submitMilestoneClaim(funding_proposal_id, 0, "ipfs://milestone-0"),
            sender=self.voter_a,
        )
        proposal3_targets = [self.treasury.address, self.treasury.address, self.funding.address]
        proposal3_values = [0, 0, 0]
        proposal3_calldatas = [
            self.treasury.functions.withdrawIdleFunds(WETH // 10)._encode_transaction_data(),
            self.treasury.functions.releaseMilestone(project_id, 0, WETH // 10)._encode_transaction_data(),
            self.funding.functions.markMilestoneReleased(funding_proposal_id, 0)._encode_transaction_data(),
        ]
        proposal3_id = self._execute_governor_proposal(
            proposer=self.voter_a,
            voters=[self.voter_a, self.voter_b, self.voter_c],
            targets=proposal3_targets,
            values=proposal3_values,
            calldatas=proposal3_calldatas,
            description="Proposal 3: release milestone 0",
            after_propose=lambda governor_proposal_id: self._send(
                self.funding.functions.linkMilestoneGovernorProposal(funding_proposal_id, 0, governor_proposal_id),
                sender=self.voter_a,
            ),
        )

        self._send(
            self.funding.functions.settleMilestoneVoteParticipationBatch(
                funding_proposal_id,
                0,
                [self.voter_a, self.voter_b, self.voter_c],
            ),
            sender=self.voter_c,
        )

        funding_project = self.funding.functions.getProject(project_id).call()
        treasury_project = self.treasury.functions.getProject(project_id).call()
        milestone0 = self.funding.functions.getMilestone(funding_proposal_id, 0).call()
        milestone1 = self.funding.functions.getMilestone(funding_proposal_id, 1).call()

        self.assertEqual(milestone0[5], proposal3_id)
        self.assertEqual(milestone0[4], 4)
        self.assertEqual(milestone1[4], 1)
        self.assertEqual(funding_project[4], WETH // 10)
        self.assertEqual(funding_project[5], 1)
        self.assertEqual(funding_project[6], 0)
        self.assertEqual(treasury_project[2], WETH // 10)
        self.assertEqual(treasury_project[4], 1)
        self.assertTrue(treasury_project[5])
        self.assertEqual(self.weth.functions.balanceOf(self.recipient).call(), WETH // 10)
        self.assertEqual(self.treasury.functions.liquidWethBalance().call(), 24 * WETH // 10)
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 5 * WETH // 10)
        self.assertEqual(self.reputation.functions.getMember(self.voter_a).call()[2], 108)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 104)
        self.assertEqual(self.reputation.functions.getMember(self.voter_c).call()[2], 104)


if __name__ == "__main__":
    unittest.main()
