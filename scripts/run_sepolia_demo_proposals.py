from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from web3 import Web3

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_SCENARIO_MANIFEST,
    DEMO_AAVE_DEPOSIT_WETH,
    DEMO_MILESTONE_PAYOUT_WETH,
    DEMO_TREASURY_FUNDING_WETH,
    PROJECT_ID,
    TOKEN_UNIT,
    VOTE_SUPPORT_FOR,
    TransactionSender,
    build_demo_scenarios,
    build_empty_evidence_manifest,
    connect_to_sepolia,
    env_default,
    load_json,
    load_required_contracts,
    parse_account_from_key,
    proposal_state_name,
    require_value,
    safe_governor_state,
    snapshot_project_state,
    snapshot_treasury_state,
    snapshot_votes,
    to_checksum_address,
    update_etherscan_links,
    wait_for_block_number,
    wait_for_timestamp,
    write_json,
)

TERMINAL_FAILURE_STATES = {2, 3, 6}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the three Sepolia Milestone 5 governance proposals.")
    parser.add_argument("--rpc-url", default=env_default("SEPOLIA_RPC_URL"))
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--scenario-output", default=str(DEFAULT_SCENARIO_MANIFEST))
    parser.add_argument("--evidence-output", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--project-recipient", default=env_default("CIF_PROJECT_RECIPIENT"))
    parser.add_argument("--voter-a-private-key", default=env_default("CIF_VOTER_A_PRIVATE_KEY"))
    parser.add_argument("--voter-b-private-key", default=env_default("CIF_VOTER_B_PRIVATE_KEY"))
    parser.add_argument("--voter-c-private-key", default=env_default("CIF_VOTER_C_PRIVATE_KEY"))
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
) -> None:
    allocation_recipients = manifest.get("allocationRecipients", {})
    for label, address in voter_addresses.items():
        if allocation_recipients.get(label) != address:
            raise RuntimeError(
                f"{label} private key resolves to {address}, but deployment manifest expects {allocation_recipients.get(label)}."
            )
        if token.functions.getVotes(address).call() == 0:
            raise RuntimeError(f"{label} has no active voting power. Run seed_sepolia_demo_state.py first.")


def persist_json(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    evidence_path: Path,
) -> None:
    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_path, evidence_manifest)


def wait_until_operation_ready(
    timelock,
    operation_id_hex: str,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> None:
    deadline = time.time() + timeout_seconds
    while not timelock.functions.isOperationReady(Web3.to_bytes(hexstr=operation_id_hex)).call():
        if time.time() > deadline:
            raise TimeoutError(f"Timed out waiting for timelock operation {operation_id_hex} to become ready.")
        time.sleep(poll_interval_seconds)


def verify_post_execution_state(
    proposal_slug: str,
    treasury,
    weth,
    project_recipient: str,
    evidence_manifest: dict[str, Any],
) -> dict[str, Any]:
    treasury_snapshot = snapshot_treasury_state(treasury)
    project_snapshot = snapshot_project_state(treasury, PROJECT_ID)
    recipient_balance = weth.functions.balanceOf(project_recipient).call()

    initial_recipient_balance = int(evidence_manifest["seedState"]["initialSnapshot"]["projectRecipientWeth"])

    if proposal_slug == "proposal1_approve_project":
        if treasury_snapshot["liquidWeth"] != str(DEMO_TREASURY_FUNDING_WETH):
            raise RuntimeError("Proposal 1 verification failed: Treasury liquid WETH does not remain at 5.0 WETH.")
        if project_snapshot["releasedWeth"] != "0" or not project_snapshot["active"]:
            raise RuntimeError("Proposal 1 verification failed: project state is inconsistent with approval-only execution.")
        if recipient_balance != initial_recipient_balance:
            raise RuntimeError("Proposal 1 verification failed: recipient balance changed before any milestone payout.")

    elif proposal_slug == "proposal2_deposit_idle_funds":
        if treasury_snapshot["liquidWeth"] != str(2 * TOKEN_UNIT):
            raise RuntimeError("Proposal 2 verification failed: Treasury liquid WETH is not 2.0 WETH.")
        if treasury_snapshot["suppliedWeth"] != str(DEMO_AAVE_DEPOSIT_WETH):
            raise RuntimeError("Proposal 2 verification failed: Treasury supplied WETH is not 3.0 WETH.")
        if treasury_snapshot["totalManagedWeth"] != str(DEMO_TREASURY_FUNDING_WETH):
            raise RuntimeError("Proposal 2 verification failed: total managed WETH drifted from 5.0 WETH.")

    elif proposal_slug == "proposal3_withdraw_and_release_milestone":
        expected_recipient_balance = initial_recipient_balance + DEMO_MILESTONE_PAYOUT_WETH
        if recipient_balance != expected_recipient_balance:
            raise RuntimeError(
                "Proposal 3 verification failed: recipient balance does not reflect the 0.5 WETH milestone payout."
            )
        if project_snapshot["releasedWeth"] != str(DEMO_MILESTONE_PAYOUT_WETH):
            raise RuntimeError("Proposal 3 verification failed: project releasedWeth is not 0.5 WETH.")
        if project_snapshot["milestonesReleased"] != 1 or not project_snapshot["active"]:
            raise RuntimeError("Proposal 3 verification failed: project milestone progression is inconsistent.")
        if treasury_snapshot["suppliedWeth"] != str((5 * TOKEN_UNIT) // 2):
            raise RuntimeError("Proposal 3 verification failed: supplied WETH is not 2.5 WETH after withdrawal.")
        if treasury_snapshot["liquidWeth"] != str(2 * TOKEN_UNIT):
            raise RuntimeError("Proposal 3 verification failed: liquid WETH is not 2.0 WETH after payout.")

    else:
        raise RuntimeError(f"Unknown proposal slug: {proposal_slug}")

    return {
        "treasury": treasury_snapshot,
        "project": project_snapshot,
        "projectRecipientWeth": str(recipient_balance),
    }


def main() -> None:
    args = parse_args()

    w3 = connect_to_sepolia(require_value(args.rpc_url, "rpc-url or SEPOLIA_RPC_URL"))
    deployment_manifest_path = Path(args.deployment_manifest)
    scenario_output_path = Path(args.scenario_output)
    evidence_output_path = Path(args.evidence_output)

    deployment_manifest = load_json(deployment_manifest_path)
    contracts = load_required_contracts(w3, deployment_manifest)
    governor = contracts["governor"]
    timelock = contracts["timelock"]
    treasury = contracts["treasury"]
    token = contracts["token"]
    weth = contracts["weth"]

    evidence_manifest = load_json(
        evidence_output_path,
        default=build_empty_evidence_manifest(deployment_manifest),
    )
    if "initialSnapshot" not in evidence_manifest.get("seedState", {}):
        raise RuntimeError("Missing seed-state evidence. Run seed_sepolia_demo_state.py before executing proposals.")
    project_recipient = resolve_project_recipient(w3, args.project_recipient, evidence_manifest)
    existing_project_recipient = evidence_manifest.get("project", {}).get("recipient")
    if existing_project_recipient is not None:
        existing_project_recipient = to_checksum_address(w3, existing_project_recipient, "existing project recipient")
        if existing_project_recipient != project_recipient:
            raise RuntimeError(
                f"Evidence manifest already records project recipient {existing_project_recipient}, not {project_recipient}."
            )
    evidence_manifest["project"] = evidence_manifest.get("project") or {}
    evidence_manifest["project"]["projectId"] = PROJECT_ID
    evidence_manifest["project"]["recipient"] = project_recipient

    voter_accounts = {
        "voterA": parse_account_from_key(require_value(args.voter_a_private_key, "voter-a-private-key")),
        "voterB": parse_account_from_key(require_value(args.voter_b_private_key, "voter-b-private-key")),
        "voterC": parse_account_from_key(require_value(args.voter_c_private_key, "voter-c-private-key")),
    }
    voter_addresses = {label: account.address for label, account in voter_accounts.items()}
    ensure_voter_configuration(deployment_manifest, voter_addresses, token)

    scenario_manifest = build_demo_scenarios(governor, timelock, treasury, project_recipient)
    scenario_manifest["network"] = deployment_manifest.get("network", {"name": "sepolia", "chainId": w3.eth.chain_id})
    scenario_manifest["contracts"] = deployment_manifest.get("contracts", {})
    write_json(scenario_output_path, scenario_manifest)

    evidence_manifest["contracts"] = deployment_manifest.get("contracts", {})
    evidence_manifest["participants"] = {
        **evidence_manifest.get("participants", {}),
        **voter_addresses,
    }

    persist_json(deployment_manifest, evidence_manifest, evidence_output_path)

    proposer_sender = TransactionSender(w3, voter_accounts["voterA"], args.gas_price_wei)
    voter_senders = {
        label: TransactionSender(w3, account, args.gas_price_wei)
        for label, account in voter_accounts.items()
    }

    for proposal in scenario_manifest["proposals"]:
        proposal_slug = proposal["slug"]
        proposal_id = int(proposal["proposalId"])
        targets = proposal["targets"]
        values = [int(value) for value in proposal["values"]]
        calldatas = proposal["calldatas"]
        description = proposal["description"]
        description_hash = proposal["descriptionHash"]
        operation_id = proposal["operationId"]

        proposal_record = evidence_manifest.setdefault("proposals", {}).setdefault(
            proposal_slug,
            {
                "title": proposal["title"],
                "description": description,
                "proposalId": proposal["proposalId"],
                "descriptionHash": description_hash,
                "operationId": operation_id,
                "transactions": {
                    "propose": None,
                    "votes": {},
                    "queue": None,
                    "execute": None,
                },
                "snapshots": {},
            },
        )

        state_value = safe_governor_state(governor, proposal_id)
        if state_value is None:
            propose_tx_hash, propose_receipt = proposer_sender.send_call(
                governor.functions.propose(targets, values, calldatas, description)
            )
            proposal_record["transactions"]["propose"] = propose_tx_hash
            proposal_record["snapshots"]["proposalCreated"] = {
                "blockNumber": propose_receipt["blockNumber"],
                "transactionHash": propose_tx_hash,
            }
            persist_json(deployment_manifest, evidence_manifest, evidence_output_path)
            state_value = governor.functions.state(proposal_id).call()

        snapshot_block = governor.functions.proposalSnapshot(proposal_id).call()
        deadline_block = governor.functions.proposalDeadline(proposal_id).call()
        proposal_record["snapshotBlock"] = snapshot_block
        proposal_record["deadlineBlock"] = deadline_block
        proposal_record["proposer"] = voter_accounts["voterA"].address

        if state_value == 0:
            wait_for_block_number(w3, snapshot_block, args.poll_interval_seconds, args.timeout_seconds)
            state_value = governor.functions.state(proposal_id).call()

        if state_value == 1:
            for label, sender in voter_senders.items():
                if governor.functions.hasVoted(proposal_id, sender.account.address).call():
                    proposal_record["transactions"]["votes"].setdefault(label, None)
                    continue
                vote_tx_hash, _ = sender.send_call(governor.functions.castVote(proposal_id, VOTE_SUPPORT_FOR))
                proposal_record["transactions"]["votes"][label] = vote_tx_hash
                persist_json(deployment_manifest, evidence_manifest, evidence_output_path)

            wait_for_block_number(w3, deadline_block + 1, args.poll_interval_seconds, args.timeout_seconds)
            state_value = governor.functions.state(proposal_id).call()

        if state_value in TERMINAL_FAILURE_STATES:
            raise RuntimeError(
                f"Proposal {proposal_slug} entered terminal failure state {proposal_state_name(state_value)}."
            )

        if state_value == 4:
            queue_tx_hash, queue_receipt = proposer_sender.send_call(
                governor.functions.queue(targets, values, calldatas, description_hash)
            )
            proposal_record["transactions"]["queue"] = queue_tx_hash
            proposal_record["queueEta"] = governor.functions.proposalEta(proposal_id).call()
            proposal_record["snapshots"]["queued"] = {
                "blockNumber": queue_receipt["blockNumber"],
                "transactionHash": queue_tx_hash,
            }
            persist_json(deployment_manifest, evidence_manifest, evidence_output_path)
            state_value = governor.functions.state(proposal_id).call()

        if state_value == 5:
            eta = governor.functions.proposalEta(proposal_id).call()
            proposal_record["queueEta"] = eta
            wait_for_timestamp(w3, eta, args.poll_interval_seconds, args.timeout_seconds)
            wait_until_operation_ready(timelock, operation_id, args.poll_interval_seconds, args.timeout_seconds)
            execute_tx_hash, execute_receipt = proposer_sender.send_call(
                governor.functions.execute(targets, values, calldatas, description_hash)
            )
            proposal_record["transactions"]["execute"] = execute_tx_hash
            proposal_record["snapshots"]["executed"] = {
                "blockNumber": execute_receipt["blockNumber"],
                "transactionHash": execute_tx_hash,
            }
            persist_json(deployment_manifest, evidence_manifest, evidence_output_path)
            state_value = governor.functions.state(proposal_id).call()

        if state_value != 7:
            raise RuntimeError(
                f"Proposal {proposal_slug} did not reach Executed state. Current state is {proposal_state_name(state_value)}."
            )

        proposal_record["finalState"] = proposal_state_name(state_value)
        proposal_record["finalVotes"] = {
            "againstVotes": str(governor.functions.proposalVotes(proposal_id).call()[0]),
            "forVotes": str(governor.functions.proposalVotes(proposal_id).call()[1]),
            "abstainVotes": str(governor.functions.proposalVotes(proposal_id).call()[2]),
        }
        proposal_record["snapshots"]["postExecution"] = verify_post_execution_state(
            proposal_slug,
            treasury,
            weth,
            project_recipient,
            evidence_manifest,
        )
        proposal_record["snapshots"]["currentVotes"] = snapshot_votes(token, voter_addresses)
        persist_json(deployment_manifest, evidence_manifest, evidence_output_path)

    print(f"Scenario manifest written to {scenario_output_path}")
    print(f"Demo evidence written to {evidence_output_path}")


if __name__ == "__main__":
    main()