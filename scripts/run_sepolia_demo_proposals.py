from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from cli_security import resolve_env_or_cli
from web3 import Web3

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_FUNDING_STATE_MANIFEST,
    DEFAULT_SCENARIO_MANIFEST,
    DEMO_AAVE_DEPOSIT_WETH,
    DEMO_MILESTONE_DESCRIPTIONS,
    DEMO_MILESTONE_EVIDENCE_URIS,
    DEMO_MILESTONE_PAYOUT_WETH,
    DEMO_POST_PROPOSAL2_LIQUID_WETH,
    DEMO_POST_PROPOSAL3_SUPPLIED_WETH,
    DEMO_POST_PROPOSAL3_TOTAL_MANAGED_WETH,
    DEMO_PROJECT_MAX_BUDGET_WETH,
    DEMO_PROPOSAL_1_DESCRIPTION,
    DEMO_PROPOSAL_2_DESCRIPTION,
    DEMO_PROPOSAL_3_DESCRIPTION,
    DEMO_PROPOSAL_METADATA_URI,
    DEMO_PROPOSAL_TITLE,
    DEMO_TREASURY_FUNDING_WETH,
    INITIAL_MEMBER_REPUTATION,
    TransactionSender,
    build_demo_scenarios,
    build_empty_evidence_manifest,
    connect_to_sepolia,
    execute_governor_proposal,
    load_json,
    load_required_contracts,
    parse_account_from_key,
    proposal_state_name,
    require_value,
    safe_governor_state,
    snapshot_milestone_state,
    snapshot_project_state,
    snapshot_proposal_state,
    snapshot_treasury_state,
    snapshot_votes,
    to_checksum_address,
    update_etherscan_links,
    write_funding_state_manifest,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the three Sepolia V2 governance proposals.",
        epilog="Prefer the *_PRIVATE_KEY environment variables over CLI flags so secrets do not end up in shell history.",
    )
    parser.add_argument("--rpc-url", default=None, help="Override SEPOLIA_RPC_URL for this run.")
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--scenario-output", default=str(DEFAULT_SCENARIO_MANIFEST))
    parser.add_argument("--evidence-output", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--funding-state-output", default=str(DEFAULT_FUNDING_STATE_MANIFEST))
    parser.add_argument("--project-recipient", default=None, help="Override CIF_PROJECT_RECIPIENT for this run.")
    parser.add_argument(
        "--voter-a-private-key",
        default=None,
        help="UNSAFE override for CIF_VOTER_A_PRIVATE_KEY. Prefer the environment variable.",
    )
    parser.add_argument(
        "--voter-b-private-key",
        default=None,
        help="UNSAFE override for CIF_VOTER_B_PRIVATE_KEY. Prefer the environment variable.",
    )
    parser.add_argument(
        "--voter-c-private-key",
        default=None,
        help="UNSAFE override for CIF_VOTER_C_PRIVATE_KEY. Prefer the environment variable.",
    )
    parser.add_argument("--poll-interval-seconds", type=float, default=6.0)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument(
        "--gas-price-wei",
        type=int,
        default=None,
        help="Override the gas price used for every transaction.",
    )
    return parser.parse_args()


def resolve_project_recipient(w3, cli_value: str | None, evidence_manifest: dict[str, Any]) -> str:
    if cli_value is not None and cli_value.strip() != "":
        return to_checksum_address(w3, cli_value, "project-recipient")

    evidence_recipient = evidence_manifest.get("project", {}).get("recipient")
    if evidence_recipient is not None:
        return to_checksum_address(w3, evidence_recipient, "evidence project recipient")

    raise ValueError("Missing required parameter: project-recipient or CIF_PROJECT_RECIPIENT")


def ensure_voter_configuration(
    manifest: dict[str, Any],
    voter_addresses: dict[str, str],
    token,
    reputation_registry,
) -> None:
    allocation_recipients = manifest.get("allocationRecipients", {})
    for label, address in voter_addresses.items():
        if allocation_recipients.get(label) != address:
            raise RuntimeError(
                f"{label} private key resolves to {address}, but deployment manifest expects {allocation_recipients.get(label)}."
            )
        if token.functions.getVotes(address).call() == 0:
            raise RuntimeError(f"{label} has no active voting power. Run seed_sepolia_demo_state.py first.")
        member = reputation_registry.functions.getMember(address).call()
        if not (bool(member[0]) and bool(member[1]) and int(member[2]) == INITIAL_MEMBER_REPUTATION):
            raise RuntimeError(
                f"{label} must be an active V2 member with exact reputation {INITIAL_MEMBER_REPUTATION}. "
                "The demo must start from the seeded baseline state."
            )


def persist_outputs(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    evidence_path: Path,
    scenario_manifest: dict[str, Any] | None,
    scenario_path: Path,
    funding_state_path: Path,
    funding_registry,
    reputation_registry,
) -> None:
    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_path, evidence_manifest)
    if scenario_manifest is not None:
        write_json(scenario_path, scenario_manifest)
    write_funding_state_manifest(funding_state_path, deployment_manifest, funding_registry, reputation_registry)


def snapshot_treasury_project_state(treasury, project_id: str) -> dict[str, Any]:
    project = treasury.functions.getProject(Web3.to_bytes(hexstr=project_id)).call()
    return {
        "recipient": project[0],
        "maxBudgetWeth": str(project[1]),
        "releasedWeth": str(project[2]),
        "milestoneCount": project[3],
        "milestonesReleased": project[4],
        "active": bool(project[5]),
    }


def verify_demo_business_proposal(
    funding_registry,
    proposal_id: int,
    proposer: str,
    recipient: str,
) -> None:
    proposal = funding_registry.functions.getProposal(proposal_id).call()
    if proposal[1] != proposer:
        raise RuntimeError(f"Funding proposal {proposal_id} proposer mismatch: expected {proposer}, got {proposal[1]}.")
    if proposal[2] != recipient:
        raise RuntimeError(f"Funding proposal {proposal_id} recipient mismatch: expected {recipient}, got {proposal[2]}.")
    if proposal[3] != DEMO_PROPOSAL_TITLE:
        raise RuntimeError(f"Funding proposal {proposal_id} title mismatch: expected {DEMO_PROPOSAL_TITLE}, got {proposal[3]}.")
    if proposal[4] != DEMO_PROPOSAL_METADATA_URI:
        raise RuntimeError(
            f"Funding proposal {proposal_id} metadataURI mismatch: expected {DEMO_PROPOSAL_METADATA_URI}, got {proposal[4]}."
        )
    if int(proposal[5]) != DEMO_PROJECT_MAX_BUDGET_WETH:
        raise RuntimeError(
            f"Funding proposal {proposal_id} requestedFunding mismatch: expected {DEMO_PROJECT_MAX_BUDGET_WETH}, got {proposal[5]}."
        )
    if int(proposal[6]) != len(DEMO_MILESTONE_DESCRIPTIONS):
        raise RuntimeError(
            f"Funding proposal {proposal_id} milestoneCount mismatch: expected {len(DEMO_MILESTONE_DESCRIPTIONS)}, got {proposal[6]}."
        )
    for milestone_index, expected_description in enumerate(DEMO_MILESTONE_DESCRIPTIONS):
        milestone = funding_registry.functions.getMilestone(proposal_id, milestone_index).call()
        if milestone[1] != expected_description:
            raise RuntimeError(
                f"Funding proposal {proposal_id} milestone {milestone_index} description mismatch: "
                f"expected {expected_description}, got {milestone[1]}."
            )
        if int(milestone[2]) != DEMO_MILESTONE_PAYOUT_WETH:
            raise RuntimeError(
                f"Funding proposal {proposal_id} milestone {milestone_index} amount mismatch: "
                f"expected {DEMO_MILESTONE_PAYOUT_WETH}, got {milestone[2]}."
            )


def find_demo_business_proposal_id(
    funding_registry,
    proposer: str,
    recipient: str,
) -> int | None:
    proposal_count = int(funding_registry.functions.proposalCount().call())
    for proposal_id in range(1, proposal_count + 1):
        try:
            verify_demo_business_proposal(funding_registry, proposal_id, proposer, recipient)
            return proposal_id
        except RuntimeError:
            continue
    return None


def ensure_business_proposal_submitted(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    proposer: str,
    recipient: str,
) -> int:
    workflow = proposal_record.setdefault("workflow", {})
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("submitFundingProposal", None)
    transactions.setdefault("linkGovernorProposal", None)
    proposal_id_raw = workflow.get("fundingProposalId")
    if proposal_id_raw is not None:
        proposal_id = int(proposal_id_raw)
        verify_demo_business_proposal(funding_registry, proposal_id, proposer, recipient)
        return proposal_id

    proposal_count_before = funding_registry.functions.proposalCount().call()
    if proposal_count_before != 0:
        existing_proposal_id = find_demo_business_proposal_id(funding_registry, proposer, recipient)
        if existing_proposal_id is None:
            raise RuntimeError(
                "FundingRegistry already contains proposals, but the evidence manifest does not record the demo funding proposal."
            )
        workflow["fundingProposalId"] = str(existing_proposal_id)
        verify_demo_business_proposal(funding_registry, existing_proposal_id, proposer, recipient)
        return existing_proposal_id

    submit_tx_hash, _ = proposer_sender.send_call(
        funding_registry.functions.submitProposal(
            DEMO_PROPOSAL_TITLE,
            DEMO_PROPOSAL_METADATA_URI,
            recipient,
            DEMO_PROJECT_MAX_BUDGET_WETH,
            DEMO_MILESTONE_DESCRIPTIONS,
            [DEMO_MILESTONE_PAYOUT_WETH, DEMO_MILESTONE_PAYOUT_WETH],
        )
    )
    deadline = time.monotonic() + 45.0
    proposal_count_after = int(funding_registry.functions.proposalCount().call())
    while proposal_count_after < proposal_count_before + 1 and time.monotonic() <= deadline:
        time.sleep(2.0)
        proposal_count_after = int(funding_registry.functions.proposalCount().call())
    if proposal_count_after != proposal_count_before + 1:
        existing_proposal_id = find_demo_business_proposal_id(funding_registry, proposer, recipient)
        if existing_proposal_id is not None:
            workflow["fundingProposalId"] = str(existing_proposal_id)
            transactions["submitFundingProposal"] = submit_tx_hash
            verify_demo_business_proposal(funding_registry, existing_proposal_id, proposer, recipient)
            return existing_proposal_id
        raise RuntimeError(
            "Funding proposal submission did not increment FundingRegistry.proposalCount() by exactly one."
        )

    proposal_id = int(proposal_count_after)
    workflow["fundingProposalId"] = str(proposal_id)
    transactions["submitFundingProposal"] = submit_tx_hash
    verify_demo_business_proposal(funding_registry, proposal_id, proposer, recipient)
    return proposal_id


def ensure_main_governor_link(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    funding_proposal_id: int,
    expected_governor_proposal_id: int,
) -> None:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("linkGovernorProposal", None)
    funding_proposal = funding_registry.functions.getProposal(funding_proposal_id).call()
    current_link = int(funding_proposal[8])
    if current_link == 0:
        link_tx_hash, _ = proposer_sender.send_call(
            funding_registry.functions.linkGovernorProposal(funding_proposal_id, expected_governor_proposal_id)
        )
        transactions["linkGovernorProposal"] = link_tx_hash
        return
    if current_link != expected_governor_proposal_id:
        raise RuntimeError(
            f"Funding proposal {funding_proposal_id} is linked to governor proposal {current_link}, not {expected_governor_proposal_id}."
        )


def ensure_milestone_claim_submitted(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    funding_proposal_id: int,
) -> None:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("submitMilestoneClaim", None)
    milestone = funding_registry.functions.getMilestone(funding_proposal_id, 0).call()
    state_value = int(milestone[4])
    evidence_uri = milestone[3]
    if state_value == 1:
        claim_tx_hash, _ = proposer_sender.send_call(
            funding_registry.functions.submitMilestoneClaim(
                funding_proposal_id,
                0,
                DEMO_MILESTONE_EVIDENCE_URIS[0],
            )
        )
        transactions["submitMilestoneClaim"] = claim_tx_hash
        return
    if state_value in {2, 4}:
        if evidence_uri != DEMO_MILESTONE_EVIDENCE_URIS[0]:
            raise RuntimeError(
                f"Milestone 0 evidence URI mismatch: expected {DEMO_MILESTONE_EVIDENCE_URIS[0]}, got {evidence_uri}."
            )
        return
    raise RuntimeError(
        f"Milestone 0 is in unexpected state {state_value} and cannot be advanced by the demo claim workflow."
    )


def ensure_milestone_governor_link(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    funding_proposal_id: int,
    expected_governor_proposal_id: int,
) -> None:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("linkMilestoneGovernorProposal", None)
    milestone = funding_registry.functions.getMilestone(funding_proposal_id, 0).call()
    current_link = int(milestone[5])
    if current_link == 0:
        link_tx_hash, _ = proposer_sender.send_call(
            funding_registry.functions.linkMilestoneGovernorProposal(
                funding_proposal_id,
                0,
                expected_governor_proposal_id,
            )
        )
        transactions["linkMilestoneGovernorProposal"] = link_tx_hash
        return
    if current_link != expected_governor_proposal_id:
        raise RuntimeError(
            "Milestone 0 is linked to an unexpected governor proposal: "
            f"expected {expected_governor_proposal_id}, got {current_link}."
        )


def ensure_governor_proposal_created(
    governor,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    scenario_entry: dict[str, Any],
    persist_callback,
) -> int:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("propose", None)
    snapshots = proposal_record.setdefault("snapshots", {})

    expected_proposal_id = int(scenario_entry["proposalId"])
    state_value = safe_governor_state(governor, expected_proposal_id)
    if state_value is not None:
        return expected_proposal_id

    propose_tx_hash, propose_receipt = proposer_sender.send_call(
        governor.functions.propose(
            scenario_entry["targets"],
            [int(value) for value in scenario_entry["values"]],
            scenario_entry["calldatas"],
            scenario_entry["description"],
        )
    )
    transactions["propose"] = propose_tx_hash
    snapshots["proposalCreated"] = {
        "blockNumber": propose_receipt["blockNumber"],
        "transactionHash": propose_tx_hash,
    }
    persist_callback()
    return expected_proposal_id


def ensure_funding_vote_participation_settled(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    funding_proposal_id: int,
    voter_addresses: dict[str, str],
) -> None:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("settleFundingVoteParticipation", None)
    settled = {
        label: bool(funding_registry.functions.hasVoteParticipationSettled(funding_proposal_id, voter).call())
        for label, voter in voter_addresses.items()
    }
    if all(settled.values()):
        if transactions["settleFundingVoteParticipation"] is None:
            raise RuntimeError(
                "Funding proposal vote participation was already settled on-chain, but the evidence manifest does "
                "not record the settlement transaction."
            )
        return
    if any(settled.values()):
        raise RuntimeError("Funding proposal vote participation is partially settled. Reset the demo state and rerun.")

    settle_tx_hash, _ = proposer_sender.send_call(
        funding_registry.functions.settleVoteParticipationBatch(
            funding_proposal_id,
            list(voter_addresses.values()),
        )
    )
    transactions["settleFundingVoteParticipation"] = settle_tx_hash


def ensure_milestone_vote_participation_settled(
    funding_registry,
    proposer_sender: TransactionSender,
    proposal_record: dict[str, Any],
    funding_proposal_id: int,
    milestone_index: int,
    voter_addresses: dict[str, str],
) -> None:
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("settleMilestoneVoteParticipation", None)
    settled = {
        label: bool(
            funding_registry.functions.hasMilestoneVoteParticipationSettled(
                funding_proposal_id,
                milestone_index,
                voter,
            ).call()
        )
        for label, voter in voter_addresses.items()
    }
    if all(settled.values()):
        if transactions["settleMilestoneVoteParticipation"] is None:
            raise RuntimeError(
                "Milestone vote participation was already settled on-chain, but the evidence manifest does not "
                "record the settlement transaction."
            )
        return
    if any(settled.values()):
        raise RuntimeError("Milestone vote participation is partially settled. Reset the demo state and rerun.")

    settle_tx_hash, _ = proposer_sender.send_call(
        funding_registry.functions.settleMilestoneVoteParticipationBatch(
            funding_proposal_id,
            milestone_index,
            list(voter_addresses.values()),
        )
    )
    transactions["settleMilestoneVoteParticipation"] = settle_tx_hash


def verify_member_reputations(
    reputation_registry,
    voter_addresses: dict[str, str],
    expected_reputations: dict[str, int],
    *,
    context: str,
) -> None:
    for label, expected in expected_reputations.items():
        member = reputation_registry.functions.getMember(voter_addresses[label]).call()
        if int(member[2]) != expected:
            raise RuntimeError(
                f"{context}: {label} reputation should be {expected}, got {member[2]}."
            )


def verify_post_execution_state(
    proposal_slug: str,
    funding_registry,
    treasury,
    weth,
    reputation_registry,
    token,
    hybrid_votes,
    voter_addresses: dict[str, str],
    funding_proposal_id: int,
    project_id: str,
    project_recipient: str,
    evidence_manifest: dict[str, Any],
) -> dict[str, Any]:
    treasury_snapshot = snapshot_treasury_state(treasury)
    funding_proposal_snapshot = snapshot_proposal_state(funding_registry, funding_proposal_id)
    project_snapshot = snapshot_project_state(funding_registry, project_id)
    treasury_project_snapshot = snapshot_treasury_project_state(treasury, project_id)
    recipient_balance = weth.functions.balanceOf(project_recipient).call()
    initial_recipient_balance = int(evidence_manifest["seedState"]["initialSnapshot"]["projectRecipientWeth"])
    milestone0_snapshot = snapshot_milestone_state(funding_registry, funding_proposal_id, 0)
    milestone1_snapshot = snapshot_milestone_state(funding_registry, funding_proposal_id, 1)
    participant_snapshot = snapshot_votes(token, voter_addresses, hybrid_votes, reputation_registry)

    if proposal_slug == "proposal1_approve_project":
        if funding_proposal_snapshot["status"] != "Approved":
            raise RuntimeError("Proposal 1 verification failed: funding proposal is not Approved.")
        if project_snapshot["approvedBudgetWeth"] != str(DEMO_PROJECT_MAX_BUDGET_WETH):
            raise RuntimeError("Proposal 1 verification failed: approved budget is not 0.2 WETH.")
        if project_snapshot["releasedWeth"] != "0" or project_snapshot["nextClaimableMilestone"] != 0:
            raise RuntimeError("Proposal 1 verification failed: project release state is inconsistent.")
        if project_snapshot["status"] != "Active" or not treasury_project_snapshot["active"]:
            raise RuntimeError("Proposal 1 verification failed: project should be active in both registries.")
        if milestone0_snapshot["state"] != "OpenForClaim" or milestone1_snapshot["state"] != "Locked":
            raise RuntimeError("Proposal 1 verification failed: milestone states are inconsistent with approval.")
        if recipient_balance != initial_recipient_balance:
            raise RuntimeError("Proposal 1 verification failed: recipient balance changed before any milestone payout.")
        if treasury_snapshot["liquidWeth"] != str(DEMO_TREASURY_FUNDING_WETH) or treasury_snapshot["suppliedWeth"] != "0":
            raise RuntimeError("Proposal 1 verification failed: treasury balances drifted during approval.")
        verify_member_reputations(
            reputation_registry,
            voter_addresses,
            {
                "voterA": INITIAL_MEMBER_REPUTATION + 2,
                "voterB": INITIAL_MEMBER_REPUTATION + 2,
                "voterC": INITIAL_MEMBER_REPUTATION + 2,
            },
            context="Proposal 1 verification failed",
        )

    elif proposal_slug == "proposal2_deposit_idle_funds":
        if treasury_snapshot["liquidWeth"] != str(DEMO_POST_PROPOSAL2_LIQUID_WETH):
            raise RuntimeError("Proposal 2 verification failed: Treasury liquid WETH is not 2.4 WETH.")
        if treasury_snapshot["suppliedWeth"] != str(DEMO_AAVE_DEPOSIT_WETH):
            raise RuntimeError("Proposal 2 verification failed: Treasury supplied WETH is not 0.6 WETH.")
        if treasury_snapshot["totalManagedWeth"] != str(DEMO_TREASURY_FUNDING_WETH):
            raise RuntimeError("Proposal 2 verification failed: total managed WETH drifted from 3.0 WETH.")
        verify_member_reputations(
            reputation_registry,
            voter_addresses,
            {
                "voterA": INITIAL_MEMBER_REPUTATION + 2,
                "voterB": INITIAL_MEMBER_REPUTATION + 2,
                "voterC": INITIAL_MEMBER_REPUTATION + 2,
            },
            context="Proposal 2 verification failed",
        )

    elif proposal_slug == "proposal3_release_milestone":
        expected_recipient_balance = initial_recipient_balance + DEMO_MILESTONE_PAYOUT_WETH
        if recipient_balance != expected_recipient_balance:
            raise RuntimeError(
                "Proposal 3 verification failed: recipient balance does not reflect the 0.1 WETH milestone payout."
            )
        if project_snapshot["releasedWeth"] != str(DEMO_MILESTONE_PAYOUT_WETH):
            raise RuntimeError("Proposal 3 verification failed: project releasedWeth is not 0.1 WETH.")
        if project_snapshot["nextClaimableMilestone"] != 1 or project_snapshot["status"] != "Active":
            raise RuntimeError("Proposal 3 verification failed: project progression is inconsistent.")
        if milestone0_snapshot["state"] != "Released" or milestone1_snapshot["state"] != "OpenForClaim":
            raise RuntimeError("Proposal 3 verification failed: milestone states are inconsistent after release.")
        if treasury_snapshot["suppliedWeth"] != str(DEMO_POST_PROPOSAL3_SUPPLIED_WETH):
            raise RuntimeError("Proposal 3 verification failed: supplied WETH is not 0.5 WETH after withdrawal.")
        if treasury_snapshot["liquidWeth"] != str(DEMO_POST_PROPOSAL2_LIQUID_WETH):
            raise RuntimeError("Proposal 3 verification failed: liquid WETH is not 2.4 WETH after payout.")
        if treasury_snapshot["totalManagedWeth"] != str(DEMO_POST_PROPOSAL3_TOTAL_MANAGED_WETH):
            raise RuntimeError("Proposal 3 verification failed: total managed WETH is not 2.9 WETH after payout.")
        verify_member_reputations(
            reputation_registry,
            voter_addresses,
            {
                "voterA": INITIAL_MEMBER_REPUTATION + 8,
                "voterB": INITIAL_MEMBER_REPUTATION + 4,
                "voterC": INITIAL_MEMBER_REPUTATION + 4,
            },
            context="Proposal 3 verification failed",
        )

    else:
        raise RuntimeError(f"Unknown proposal slug: {proposal_slug}")

    return {
        "treasury": treasury_snapshot,
        "fundingProposal": funding_proposal_snapshot,
        "fundingProject": project_snapshot,
        "treasuryProject": treasury_project_snapshot,
        "milestone0": milestone0_snapshot,
        "milestone1": milestone1_snapshot,
        "projectRecipientWeth": str(recipient_balance),
        "participants": participant_snapshot,
    }


def main() -> None:
    args = parse_args()

    rpc_url = require_value(
        resolve_env_or_cli(args.rpc_url, "SEPOLIA_RPC_URL", cli_flag="--rpc-url"),
        "rpc-url or SEPOLIA_RPC_URL",
    )
    w3 = connect_to_sepolia(rpc_url)
    deployment_manifest_path = Path(args.deployment_manifest)
    scenario_output_path = Path(args.scenario_output)
    evidence_output_path = Path(args.evidence_output)
    funding_state_output_path = Path(args.funding_state_output)

    deployment_manifest = load_json(deployment_manifest_path)
    contracts = load_required_contracts(w3, deployment_manifest)
    token = contracts["token"]
    reputation = contracts["reputation"]
    hybrid_votes = contracts["hybridVotes"]
    governor = contracts["governor"]
    funding_registry = contracts["fundingRegistry"]
    timelock = contracts["timelock"]
    treasury = contracts["treasury"]
    weth = contracts["weth"]

    evidence_manifest = load_json(
        evidence_output_path,
        default=build_empty_evidence_manifest(deployment_manifest),
    )
    if "initialSnapshot" not in evidence_manifest.get("seedState", {}):
        raise RuntimeError("Missing seed-state evidence. Run seed_sepolia_demo_state.py before executing proposals.")

    project_recipient = resolve_project_recipient(
        w3,
        resolve_env_or_cli(args.project_recipient, "CIF_PROJECT_RECIPIENT", cli_flag="--project-recipient"),
        evidence_manifest,
    )

    voter_accounts = {
        "voterA": parse_account_from_key(
            require_value(
                resolve_env_or_cli(
                    args.voter_a_private_key,
                    "CIF_VOTER_A_PRIVATE_KEY",
                    cli_flag="--voter-a-private-key",
                    sensitive=True,
                ),
                "CIF_VOTER_A_PRIVATE_KEY or --voter-a-private-key",
            )
        ),
        "voterB": parse_account_from_key(
            require_value(
                resolve_env_or_cli(
                    args.voter_b_private_key,
                    "CIF_VOTER_B_PRIVATE_KEY",
                    cli_flag="--voter-b-private-key",
                    sensitive=True,
                ),
                "CIF_VOTER_B_PRIVATE_KEY or --voter-b-private-key",
            )
        ),
        "voterC": parse_account_from_key(
            require_value(
                resolve_env_or_cli(
                    args.voter_c_private_key,
                    "CIF_VOTER_C_PRIVATE_KEY",
                    cli_flag="--voter-c-private-key",
                    sensitive=True,
                ),
                "CIF_VOTER_C_PRIVATE_KEY or --voter-c-private-key",
            )
        ),
    }
    voter_addresses = {label: account.address for label, account in voter_accounts.items()}
    ensure_voter_configuration(deployment_manifest, voter_addresses, token, reputation)

    evidence_manifest["contracts"] = deployment_manifest.get("contracts", {})
    evidence_manifest["participants"] = {
        **evidence_manifest.get("participants", {}),
        **voter_addresses,
    }
    evidence_manifest["project"] = evidence_manifest.get("project") or {}
    evidence_manifest["project"]["name"] = evidence_manifest["project"].get("name") or "Smart Recycling Kiosk"
    evidence_manifest["project"]["projectKey"] = evidence_manifest["project"].get("projectKey") or "SMART_RECYCLING_KIOSK"
    evidence_manifest["project"]["recipient"] = project_recipient

    proposer_sender = TransactionSender(w3, voter_accounts["voterA"], args.gas_price_wei)
    voter_senders = {
        label: TransactionSender(w3, account, args.gas_price_wei)
        for label, account in voter_accounts.items()
    }

    proposal1_record = evidence_manifest.setdefault("proposals", {}).setdefault(
        "proposal1_approve_project",
        {
            "title": "Proposal 1",
            "description": DEMO_PROPOSAL_1_DESCRIPTION,
            "transactions": {},
            "snapshots": {},
            "workflow": {},
        },
    )
    funding_proposal_id = ensure_business_proposal_submitted(
        funding_registry,
        proposer_sender,
        proposal1_record,
        proposer_sender.account.address,
        project_recipient,
    )

    scenario_manifest = build_demo_scenarios(
        governor=governor,
        timelock=timelock,
        treasury=treasury,
        funding_registry=funding_registry,
        proposer=proposer_sender.account.address,
        recipient=project_recipient,
        voter_addresses=voter_addresses,
        funding_proposal_id=funding_proposal_id,
    )
    scenario_manifest["network"] = deployment_manifest.get("network", {"name": "sepolia", "chainId": w3.eth.chain_id})
    scenario_manifest["contracts"] = deployment_manifest.get("contracts", {})
    project = scenario_manifest["project"]
    project_id = project["projectId"]

    evidence_manifest["project"].update(project)

    def persist_callback() -> None:
        persist_outputs(
            deployment_manifest,
            evidence_manifest,
            evidence_output_path,
            scenario_manifest,
            scenario_output_path,
            funding_state_output_path,
            funding_registry,
            reputation,
        )

    proposal_specs = {entry["slug"]: entry for entry in scenario_manifest["proposals"]}
    persist_callback()
    proposal1_record["workflow"].update(proposal_specs["proposal1_approve_project"]["workflow"])
    proposal1_record["workflow"]["fundingProposalId"] = str(funding_proposal_id)
    ensure_governor_proposal_created(
        governor,
        proposer_sender,
        proposal1_record,
        proposal_specs["proposal1_approve_project"],
        persist_callback,
    )
    ensure_main_governor_link(
        funding_registry,
        proposer_sender,
        proposal1_record,
        funding_proposal_id,
        int(proposal_specs["proposal1_approve_project"]["proposalId"]),
    )
    persist_callback()

    for slug in ("proposal2_deposit_idle_funds", "proposal3_release_milestone"):
        record = evidence_manifest.setdefault("proposals", {}).setdefault(
            slug,
            {
                "title": "Proposal 2" if slug == "proposal2_deposit_idle_funds" else "Proposal 3",
                "description": DEMO_PROPOSAL_2_DESCRIPTION if slug == "proposal2_deposit_idle_funds" else DEMO_PROPOSAL_3_DESCRIPTION,
                "transactions": {},
                "snapshots": {},
                "workflow": {},
            },
        )
        record["workflow"].update(proposal_specs[slug]["workflow"])

    proposal_order = [
        ("proposal1_approve_project", proposal1_record),
        ("proposal2_deposit_idle_funds", evidence_manifest["proposals"]["proposal2_deposit_idle_funds"]),
        ("proposal3_release_milestone", evidence_manifest["proposals"]["proposal3_release_milestone"]),
    ]

    for proposal_slug, proposal_record in proposal_order:
        scenario_entry = proposal_specs[proposal_slug]
        if proposal_slug == "proposal3_release_milestone":
            ensure_milestone_claim_submitted(funding_registry, proposer_sender, proposal_record, funding_proposal_id)
            persist_callback()
            ensure_governor_proposal_created(
                governor,
                proposer_sender,
                proposal_record,
                scenario_entry,
                persist_callback,
            )
            ensure_milestone_governor_link(
                funding_registry,
                proposer_sender,
                proposal_record,
                funding_proposal_id,
                int(scenario_entry["proposalId"]),
            )
            persist_callback()

        proposal_record["title"] = scenario_entry["title"]
        proposal_record["description"] = scenario_entry["description"]
        proposal_record["workflow"].update(scenario_entry["workflow"])

        proposal_id, state_value = execute_governor_proposal(
            w3=w3,
            governor=governor,
            timelock=timelock,
            proposer_sender=proposer_sender,
            voter_senders=voter_senders,
            proposal_record=proposal_record,
            targets=scenario_entry["targets"],
            values=[int(value) for value in scenario_entry["values"]],
            calldatas=scenario_entry["calldatas"],
            description=scenario_entry["description"],
            poll_interval_seconds=args.poll_interval_seconds,
            timeout_seconds=args.timeout_seconds,
            persist_callback=persist_callback,
        )
        if state_value != 7:
            raise RuntimeError(
                f"Proposal {proposal_slug} did not reach Executed state. Current state is {proposal_state_name(state_value)}."
            )

        proposal_record["workflow"]["governorProposalId"] = str(proposal_id)

        if proposal_slug == "proposal1_approve_project":
            ensure_funding_vote_participation_settled(
                funding_registry,
                proposer_sender,
                proposal_record,
                funding_proposal_id,
                voter_addresses,
            )
            persist_callback()
        elif proposal_slug == "proposal3_release_milestone":
            ensure_milestone_vote_participation_settled(
                funding_registry,
                proposer_sender,
                proposal_record,
                funding_proposal_id,
                0,
                voter_addresses,
            )
            persist_callback()

        proposal_record["snapshots"]["postExecution"] = verify_post_execution_state(
            proposal_slug=proposal_slug,
            funding_registry=funding_registry,
            treasury=treasury,
            weth=weth,
            reputation_registry=reputation,
            token=token,
            hybrid_votes=hybrid_votes,
            voter_addresses=voter_addresses,
            funding_proposal_id=funding_proposal_id,
            project_id=project_id,
            project_recipient=project_recipient,
            evidence_manifest=evidence_manifest,
        )
        proposal_record["snapshots"]["currentVotes"] = snapshot_votes(token, voter_addresses, hybrid_votes, reputation)
        persist_callback()

    print(f"Scenario manifest written to {scenario_output_path}")
    print(f"Demo evidence written to {evidence_output_path}")
    print(f"Funding state manifest written to {funding_state_output_path}")


if __name__ == "__main__":
    main()
