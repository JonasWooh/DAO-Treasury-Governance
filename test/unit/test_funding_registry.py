from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact, predict_create_address


WETH = 10**18
PENDING = 0
CANCELED = 2
DEFEATED = 3
EXECUTED = 7


class FundingRegistryUnitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "funding": load_artifact("src/funding/FundingRegistry/FundingRegistry.json"),
            "reputation": load_artifact("src/governance/ReputationRegistry/ReputationRegistry.json"),
            "mock_governor": load_artifact("src/mocks/MockInnovationGovernor/MockInnovationGovernor.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.owner = self.w3.eth.accounts[0]
        self.proposer = self.w3.eth.accounts[1]
        self.voter_b = self.w3.eth.accounts[2]
        self.voter_c = self.w3.eth.accounts[3]
        self.recipient = self.w3.eth.accounts[4]

        self.mock_governor = self._deploy("mock_governor", [])
        predicted_funding = predict_create_address(self.owner, self.w3.eth.get_transaction_count(self.owner) + 1)
        self.reputation = self._deploy("reputation", [self.owner, predicted_funding])
        self.funding = self._deploy("funding", [self.owner, self.mock_governor.address, self.reputation.address])

        for member in (self.proposer, self.voter_b, self.voter_c):
            self._send(self.reputation.functions.registerMember(member, 100))

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.owner})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, *, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.owner})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _assert_reverts(self, fn) -> None:
        with self.assertRaises(TransactionFailed):
            fn()

    def _set_governor_state(self, proposal_id: int, state: int) -> None:
        self._send(self.mock_governor.functions.setProposalState(proposal_id, state))

    def _set_has_voted(self, proposal_id: int, voter: str, has_voted: bool = True) -> None:
        self._send(self.mock_governor.functions.setHasVoted(proposal_id, voter, has_voted))

    def _submit_proposal(
        self,
        *,
        milestone_amounts: list[int],
        requested_funding: int | None = None,
        recipient: str | None = None,
        sender: str | None = None,
    ) -> int:
        descriptions = [f"Milestone {index}" for index in range(len(milestone_amounts))]
        requested = requested_funding if requested_funding is not None else sum(milestone_amounts)
        self._send(
            self.funding.functions.submitProposal(
                "Smart Recycling Kiosk",
                "ipfs://proposal-metadata",
                recipient or self.recipient,
                requested,
                descriptions,
                milestone_amounts,
            ),
            sender=sender or self.proposer,
        )
        return int(self.funding.functions.proposalCount().call())

    def _link_main_governor_proposal(self, proposal_id: int, governor_proposal_id: int) -> None:
        self._set_governor_state(governor_proposal_id, PENDING)
        self._send(
            self.funding.functions.linkGovernorProposal(proposal_id, governor_proposal_id),
            sender=self.proposer,
        )

    def _approve_project(self, proposal_id: int, governor_proposal_id: int) -> bytes:
        self._link_main_governor_proposal(proposal_id, governor_proposal_id)
        self._set_governor_state(governor_proposal_id, EXECUTED)
        project_id = self.funding.functions.deriveProjectId(proposal_id, self.proposer, self.recipient).call()
        self._send(self.funding.functions.markProposalApproved(proposal_id, project_id))
        return project_id

    def _submit_claim_and_link(
        self,
        proposal_id: int,
        milestone_index: int,
        claim_governor_proposal_id: int,
        evidence_uri: str | None = None,
    ) -> None:
        self._send(
            self.funding.functions.submitMilestoneClaim(
                proposal_id,
                milestone_index,
                evidence_uri or f"ipfs://milestone-{milestone_index}",
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

    def test_submit_proposal_validates_recipient_and_milestone_sum(self):
        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.submitProposal(
                    "Smart Recycling Kiosk",
                    "ipfs://proposal-metadata",
                    "0x0000000000000000000000000000000000000000",
                    WETH,
                    ["Milestone 0", "Milestone 1"],
                    [WETH // 2, WETH // 2],
                ),
                sender=self.proposer,
            )
        )
        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.submitProposal(
                    "Smart Recycling Kiosk",
                    "ipfs://proposal-metadata",
                    self.recipient,
                    WETH,
                    ["Milestone 0", "Milestone 1"],
                    [WETH // 2, WETH // 4],
                ),
                sender=self.proposer,
            )
        )

        proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        proposal = self.funding.functions.getProposal(proposal_id).call()
        milestone0 = self.funding.functions.getMilestone(proposal_id, 0).call()
        milestone1 = self.funding.functions.getMilestone(proposal_id, 1).call()

        self.assertEqual(proposal[2], self.recipient)
        self.assertEqual(proposal[5], WETH)
        self.assertEqual(proposal[6], 2)
        self.assertEqual(milestone0[2], WETH // 2)
        self.assertEqual(milestone1[2], WETH // 2)

    def test_mark_proposal_approved_creates_project_and_opens_first_milestone(self):
        proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        project_id = self._approve_project(proposal_id, 101)

        proposal = self.funding.functions.getProposal(proposal_id).call()
        project = self.funding.functions.getProject(project_id).call()
        milestone0 = self.funding.functions.getMilestone(proposal_id, 0).call()
        milestone1 = self.funding.functions.getMilestone(proposal_id, 1).call()

        self.assertEqual(proposal[7], 2)
        self.assertEqual(Web3.to_hex(proposal[9]), Web3.to_hex(project_id))
        self.assertEqual(Web3.to_hex(project[0]), Web3.to_hex(project_id))
        self.assertEqual(project[2], self.recipient)
        self.assertEqual(project[3], WETH)
        self.assertEqual(project[4], 0)
        self.assertEqual(project[5], 0)
        self.assertEqual(project[6], 0)
        self.assertEqual(milestone0[4], 1)
        self.assertEqual(milestone1[4], 0)

    def test_finalize_proposal_outcome_sets_rejected_or_cancelled(self):
        rejected_proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        self._link_main_governor_proposal(rejected_proposal_id, 101)
        self._set_governor_state(101, DEFEATED)
        self._send(self.funding.functions.finalizeProposalOutcome(rejected_proposal_id), sender=self.voter_b)
        self.assertEqual(self.funding.functions.getProposal(rejected_proposal_id).call()[7], 3)

        cancelled_proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        self._link_main_governor_proposal(cancelled_proposal_id, 102)
        self._set_governor_state(102, CANCELED)
        self._send(self.funding.functions.finalizeProposalOutcome(cancelled_proposal_id), sender=self.voter_c)
        self.assertEqual(self.funding.functions.getProposal(cancelled_proposal_id).call()[7], 4)

    def test_mark_milestone_released_applies_plus_four_and_completion_bonus(self):
        proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        project_id = self._approve_project(proposal_id, 101)

        self._submit_claim_and_link(proposal_id, 0, 201)
        self._set_governor_state(201, EXECUTED)
        self._send(self.funding.functions.markMilestoneReleased(proposal_id, 0))

        project_after_first_release = self.funding.functions.getProject(project_id).call()
        proposer_after_first_release = self.reputation.functions.getMember(self.proposer).call()
        self.assertEqual(project_after_first_release[4], WETH // 2)
        self.assertEqual(project_after_first_release[5], 1)
        self.assertEqual(project_after_first_release[6], 0)
        self.assertEqual(proposer_after_first_release[2], 104)

        self._submit_claim_and_link(proposal_id, 1, 202)
        self._set_governor_state(202, EXECUTED)
        self._send(self.funding.functions.markMilestoneReleased(proposal_id, 1))

        completed_project = self.funding.functions.getProject(project_id).call()
        completed_member = self.reputation.functions.getMember(self.proposer).call()
        self.assertEqual(completed_project[4], WETH)
        self.assertEqual(completed_project[5], 2)
        self.assertEqual(completed_project[6], 1)
        self.assertEqual(completed_member[2], 118)

    def test_finalize_milestone_outcome_applies_minus_eight(self):
        proposal_id = self._submit_proposal(milestone_amounts=[WETH])
        self._approve_project(proposal_id, 101)
        self._submit_claim_and_link(proposal_id, 0, 201)
        self._set_governor_state(201, DEFEATED)

        self._send(self.funding.functions.finalizeMilestoneOutcome(proposal_id, 0), sender=self.voter_b)

        milestone = self.funding.functions.getMilestone(proposal_id, 0).call()
        member = self.reputation.functions.getMember(self.proposer).call()
        self.assertEqual(milestone[4], 3)
        self.assertEqual(member[2], 92)

    def test_settle_vote_participation_batch_is_one_time(self):
        proposal_id = self._submit_proposal(milestone_amounts=[WETH // 2, WETH // 2])
        self._approve_project(proposal_id, 101)

        self._set_has_voted(101, self.proposer, True)
        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.settleVoteParticipationBatch(proposal_id, [self.proposer, self.voter_b]),
                sender=self.voter_c,
            )
        )

        self._set_has_voted(101, self.voter_b, True)
        self._send(
            self.funding.functions.settleVoteParticipationBatch(proposal_id, [self.proposer, self.voter_b]),
            sender=self.voter_c,
        )

        self.assertTrue(self.funding.functions.hasVoteParticipationSettled(proposal_id, self.proposer).call())
        self.assertTrue(self.funding.functions.hasVoteParticipationSettled(proposal_id, self.voter_b).call())
        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 102)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 102)

        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.settleVoteParticipationBatch(proposal_id, [self.proposer]),
                sender=self.voter_c,
            )
        )

    def test_settle_milestone_vote_participation_batch_is_one_time_and_requires_terminal_milestone(self):
        proposal_id = self._submit_proposal(milestone_amounts=[WETH])
        self._approve_project(proposal_id, 101)
        self._submit_claim_and_link(proposal_id, 0, 201)

        self._set_has_voted(201, self.proposer, True)
        self._set_has_voted(201, self.voter_b, True)

        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.settleMilestoneVoteParticipationBatch(proposal_id, 0, [self.proposer, self.voter_b]),
                sender=self.voter_c,
            )
        )

        self._set_governor_state(201, EXECUTED)
        self._send(self.funding.functions.markMilestoneReleased(proposal_id, 0))
        self._send(
            self.funding.functions.settleMilestoneVoteParticipationBatch(proposal_id, 0, [self.proposer, self.voter_b]),
            sender=self.voter_c,
        )

        self.assertTrue(
            self.funding.functions.hasMilestoneVoteParticipationSettled(proposal_id, 0, self.proposer).call()
        )
        self.assertTrue(
            self.funding.functions.hasMilestoneVoteParticipationSettled(proposal_id, 0, self.voter_b).call()
        )
        self.assertEqual(self.reputation.functions.getMember(self.proposer).call()[2], 116)
        self.assertEqual(self.reputation.functions.getMember(self.voter_b).call()[2], 102)

        self._assert_reverts(
            lambda: self._send(
                self.funding.functions.settleMilestoneVoteParticipationBatch(proposal_id, 0, [self.proposer]),
                sender=self.voter_c,
            )
        )


if __name__ == "__main__":
    unittest.main()
