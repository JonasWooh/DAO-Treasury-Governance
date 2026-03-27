from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact, predict_create_address


WETH = 10**18
PENDING = 0
DEFEATED = 3
EXECUTED = 7


class FundingWorkflowIntegrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "funding": load_artifact("src/funding/FundingRegistry/FundingRegistry.json"),
            "reputation": load_artifact("src/governance/ReputationRegistry/ReputationRegistry.json"),
            "mock_governor": load_artifact("src/mocks/MockInnovationGovernor/MockInnovationGovernor.json"),
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
        self.proposer = self.w3.eth.accounts[1]
        self.voter_b = self.w3.eth.accounts[2]
        self.voter_c = self.w3.eth.accounts[3]
        self.recipient = self.w3.eth.accounts[4]

        self.mock_governor = self._deploy("mock_governor", [])
        predicted_funding = predict_create_address(self.deployer, self.w3.eth.get_transaction_count(self.deployer) + 1)
        self.reputation = self._deploy("reputation", [self.deployer, predicted_funding])
        self.funding = self._deploy("funding", [self.deployer, self.mock_governor.address, self.reputation.address])

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
            [self.deployer, self.weth.address, self.oracle.address, self.adapter.address, self.funding.address],
        )
        self.assertEqual(self.treasury.address, predicted_treasury)

        self._send(self.chainlink.functions.setRoundData(2_000 * 10**8, self._latest_timestamp(), 8))
        self._send(self.weth.functions.mint(self.treasury.address, 3 * WETH))

        for member in (self.proposer, self.voter_b, self.voter_c):
            self._send(self.reputation.functions.registerMember(member, 100))

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, *, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.deployer})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _assert_reverts(self, fn) -> None:
        with self.assertRaises(TransactionFailed):
            fn()

    def _latest_timestamp(self) -> int:
        return self.eth_tester.get_block_by_number("latest")["timestamp"]

    def _set_governor_state(self, proposal_id: int, state: int) -> None:
        self._send(self.mock_governor.functions.setProposalState(proposal_id, state))

    def _set_has_voted(self, proposal_id: int, voter: str, has_voted: bool = True) -> None:
        self._send(self.mock_governor.functions.setHasVoted(proposal_id, voter, has_voted))

    def _submit_funding_proposal(self, milestone_amounts: list[int]) -> int:
        self._send(
            self.funding.functions.submitProposal(
                "Smart Recycling Kiosk",
                "ipfs://proposal-metadata",
                self.recipient,
                sum(milestone_amounts),
                [f"Milestone {index}" for index in range(len(milestone_amounts))],
                milestone_amounts,
            ),
            sender=self.proposer,
        )
        return int(self.funding.functions.proposalCount().call())

    def _approve_project_in_both_registries(
        self,
        proposal_id: int,
        governor_proposal_id: int,
        budget_weth: int,
        milestone_count: int,
    ) -> bytes:
        self._set_governor_state(governor_proposal_id, PENDING)
        self._send(
            self.funding.functions.linkGovernorProposal(proposal_id, governor_proposal_id),
            sender=self.proposer,
        )
        self._set_governor_state(governor_proposal_id, EXECUTED)
        project_id = self.funding.functions.deriveProjectId(proposal_id, self.proposer, self.recipient).call()
        self._send(self.funding.functions.markProposalApproved(proposal_id, project_id))
        self._send(self.treasury.functions.approveProject(project_id, self.recipient, budget_weth, milestone_count))
        return project_id

    def _submit_claim_and_link(self, proposal_id: int, milestone_index: int, claim_governor_proposal_id: int) -> None:
        self._send(
            self.funding.functions.submitMilestoneClaim(
                proposal_id,
                milestone_index,
                f"ipfs://milestone-{milestone_index}",
            ),
            sender=self.proposer,
        )
        self._set_governor_state(claim_governor_proposal_id, PENDING)
        self._send(
            self.funding.functions.linkMilestoneGovernorProposal(
                proposal_id,
                milestone_index,
                claim_governor_proposal_id,
            ),
            sender=self.proposer,
        )

    def test_happy_path_release_and_separate_settlement(self):
        proposal_id = self._submit_funding_proposal([WETH // 10, WETH // 10])
        project_id = self._approve_project_in_both_registries(proposal_id, 101, WETH // 5, 2)

        for voter in (self.proposer, self.voter_b, self.voter_c):
            self._set_has_voted(101, voter, True)
        self._send(
            self.funding.functions.settleVoteParticipationBatch(
                proposal_id,
                [self.proposer, self.voter_b, self.voter_c],
            ),
            sender=self.voter_c,
        )
        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_c).call()[2], 102)

        self._submit_claim_and_link(proposal_id, 0, 201)
        self._set_governor_state(201, EXECUTED)

        self._send(self.treasury.functions.depositIdleFunds(6 * WETH // 10))
        self._send(self.treasury.functions.withdrawIdleFunds(WETH // 10))
        self._send(self.treasury.functions.releaseMilestone(project_id, 0, WETH // 10))
        self._send(self.funding.functions.markMilestoneReleased(proposal_id, 0))

        funding_project = self.funding.functions.getProject(project_id).call()
        treasury_project = self.treasury.functions.getProject(project_id).call()
        milestone0 = self.funding.functions.getMilestone(proposal_id, 0).call()
        milestone1 = self.funding.functions.getMilestone(proposal_id, 1).call()

        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 106)
        self.assertEqual(funding_project[4], WETH // 10)
        self.assertEqual(funding_project[5], 1)
        self.assertEqual(funding_project[6], 0)
        self.assertEqual(treasury_project[2], WETH // 10)
        self.assertEqual(treasury_project[4], 1)
        self.assertTrue(treasury_project[5])
        self.assertEqual(milestone0[4], 4)
        self.assertEqual(milestone1[4], 1)
        self.assertEqual(self.weth.functions.balanceOf(self.recipient).call(), WETH // 10)
        self.assertEqual(self.treasury.functions.liquidWethBalance().call(), 24 * WETH // 10)
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 5 * WETH // 10)

        for voter in (self.proposer, self.voter_b, self.voter_c):
            self._set_has_voted(201, voter, True)
        self._send(
            self.funding.functions.settleMilestoneVoteParticipationBatch(
                proposal_id,
                0,
                [self.proposer, self.voter_b, self.voter_c],
            ),
            sender=self.voter_c,
        )

        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 108)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 104)
        self.assertEqual(self.reputation.functions.getMember(self.voter_c).call()[2], 104)

    def test_finalize_proposal_rejected_leaves_treasury_untouched(self):
        proposal_id = self._submit_funding_proposal([WETH // 10, WETH // 10])
        self._set_governor_state(101, PENDING)
        self._send(self.funding.functions.linkGovernorProposal(proposal_id, 101), sender=self.proposer)
        self._set_governor_state(101, DEFEATED)

        self._send(self.funding.functions.finalizeProposalOutcome(proposal_id), sender=self.voter_b)

        proposal = self.funding.functions.getProposal(proposal_id).call()
        self.assertEqual(proposal[7], 3)
        self.assertEqual(self.funding.functions.projectCount().call(), 0)
        self.assertEqual(self.treasury.functions.totalManagedWeth().call(), 3 * WETH)
        self.assertEqual(self.weth.functions.balanceOf(self.recipient).call(), 0)

    def test_finalize_milestone_rejected_applies_minus_eight_and_no_release(self):
        proposal_id = self._submit_funding_proposal([WETH // 2])
        project_id = self._approve_project_in_both_registries(proposal_id, 101, WETH // 2, 1)
        self._submit_claim_and_link(proposal_id, 0, 201)
        self._set_governor_state(201, DEFEATED)

        self._send(self.funding.functions.finalizeMilestoneOutcome(proposal_id, 0), sender=self.voter_b)

        milestone = self.funding.functions.getMilestone(proposal_id, 0).call()
        funding_project = self.funding.functions.getProject(project_id).call()
        treasury_project = self.treasury.functions.getProject(project_id).call()
        self.assertEqual(milestone[4], 3)
        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 92)
        self.assertEqual(funding_project[4], 0)
        self.assertEqual(treasury_project[2], 0)
        self.assertEqual(self.weth.functions.balanceOf(self.recipient).call(), 0)

    def test_duplicate_settlement_does_not_block_release_when_done_separately(self):
        proposal_id = self._submit_funding_proposal([WETH // 2])
        project_id = self._approve_project_in_both_registries(proposal_id, 101, WETH // 2, 1)
        self._submit_claim_and_link(proposal_id, 0, 201)
        self._set_governor_state(201, EXECUTED)
        self._send(self.treasury.functions.releaseMilestone(project_id, 0, WETH // 2))
        self._send(self.funding.functions.markMilestoneReleased(proposal_id, 0))

        for voter in (self.proposer, self.voter_b):
            self._set_has_voted(201, voter, True)
        self._send(
            self.funding.functions.settleMilestoneVoteParticipationBatch(
                proposal_id,
                0,
                [self.proposer, self.voter_b],
            ),
            sender=self.voter_c,
        )

        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.settleMilestoneVoteParticipationBatch(
                    proposal_id,
                    0,
                    [self.proposer],
                ),
                sender=self.voter_c,
            )
        )

        funding_project = self.funding.functions.getProject(project_id).call()
        treasury_project = self.treasury.functions.getProject(project_id).call()
        self.assertEqual(funding_project[4], WETH // 2)
        self.assertEqual(funding_project[6], 1)
        self.assertEqual(treasury_project[2], WETH // 2)
        self.assertEqual(self.weth.functions.balanceOf(self.recipient).call(), WETH // 2)


if __name__ == "__main__":
    unittest.main()
