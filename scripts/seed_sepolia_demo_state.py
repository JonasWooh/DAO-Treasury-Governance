from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_FUNDING_STATE_MANIFEST,
    DEMO_BOOTSTRAP_DESCRIPTION,
    DEMO_TREASURY_FUNDING_WETH,
    INITIAL_MEMBER_REPUTATION,
    INITIAL_VOTER_ALLOCATION,
    TOKEN_UNIT,
    ZERO_ADDRESS,
    TransactionSender,
    build_empty_evidence_manifest,
    connect_to_sepolia,
    encode_call,
    env_default,
    execute_governor_proposal,
    load_json,
    load_required_contracts,
    parse_account_from_key,
    require_value,
    snapshot_treasury_state,
    snapshot_votes,
    to_checksum_address,
    update_etherscan_links,
    write_funding_state_manifest,
    write_json,
)

DEFAULT_MIN_LIQUID_RESERVE_BPS = 3000
DEFAULT_MAX_SINGLE_GRANT_BPS = 2000
DEFAULT_STALE_PRICE_THRESHOLD = 3600


def wait_for_self_delegation(
    token,
    address: str,
    expected_votes: int,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> int:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        delegate = token.functions.delegates(address).call()
        votes = token.functions.getVotes(address).call()
        if delegate == address and votes == expected_votes:
            return votes
        time.sleep(poll_interval_seconds)
    return token.functions.getVotes(address).call()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the Sepolia V2 demo state.")
    parser.add_argument("--rpc-url", default=env_default("SEPOLIA_RPC_URL"))
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--evidence-output", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--funding-state-output", default=str(DEFAULT_FUNDING_STATE_MANIFEST))
    parser.add_argument("--project-recipient", default=env_default("CIF_PROJECT_RECIPIENT"))
    parser.add_argument("--funder-private-key", default=env_default("CIF_TREASURY_FUNDER_PRIVATE_KEY"))
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


def ensure_voter_configuration(
    manifest: dict[str, Any],
    voter_addresses: dict[str, str],
    token,
) -> None:
    allocation_recipients = manifest.get("allocationRecipients", {})
    initial_allocations = manifest.get("config", {}).get("initialAllocations", {})

    for label, address in voter_addresses.items():
        if allocation_recipients.get(label) != address:
            raise RuntimeError(
                f"{label} private key resolves to {address}, but deployment manifest expects {allocation_recipients.get(label)}."
            )

        token_balance = token.functions.balanceOf(address).call()
        expected_balance = int(initial_allocations.get(label, INITIAL_VOTER_ALLOCATION))
        if token_balance != expected_balance:
            raise RuntimeError(
                f"{label} token balance mismatch: expected {expected_balance}, got {token_balance}."
            )


def persist_outputs(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    evidence_output_path: Path,
    funding_state_output_path: Path,
    funding_registry,
    reputation_registry,
) -> None:
    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_output_path, evidence_manifest)
    write_funding_state_manifest(funding_state_output_path, deployment_manifest, funding_registry, reputation_registry)


def member_snapshot(reputation_registry, voter_addresses: dict[str, str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for label, address in voter_addresses.items():
        member = reputation_registry.functions.getMember(address).call()
        snapshot[label] = {
            "address": address,
            "isRegistered": bool(member[0]),
            "isActive": bool(member[1]),
            "currentReputation": str(member[2]),
        }
    return snapshot


def ensure_members_bootstrapped(
    w3,
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    evidence_output_path: Path,
    funding_state_output_path: Path,
    voter_accounts: dict[str, Any],
    voter_addresses: dict[str, str],
    governor,
    timelock,
    funding_registry,
    reputation_registry,
    poll_interval_seconds: float,
    timeout_seconds: float,
    gas_price_wei: int | None,
) -> None:
    member_count = reputation_registry.functions.memberCount().call()
    member_states = {
        label: reputation_registry.functions.getMember(address).call()
        for label, address in voter_addresses.items()
    }
    all_registered = all(bool(state[0]) and bool(state[1]) and int(state[2]) == INITIAL_MEMBER_REPUTATION for state in member_states.values())

    bootstrap_record = evidence_manifest.setdefault("seedState", {}).setdefault(
        "bootstrapMembers",
        {
            "description": DEMO_BOOTSTRAP_DESCRIPTION,
            "initialReputation": str(INITIAL_MEMBER_REPUTATION),
            "memberAddresses": voter_addresses,
            "transactions": {
                "propose": None,
                "votes": {},
                "queue": None,
                "execute": None,
            },
            "snapshots": {},
        },
    )

    def persist_callback() -> None:
        persist_outputs(
            deployment_manifest,
            evidence_manifest,
            evidence_output_path,
            funding_state_output_path,
            funding_registry,
            reputation_registry,
        )

    if all_registered:
        if member_count != len(voter_addresses):
            raise RuntimeError(
                f"Reputation registry member count drift detected: expected {len(voter_addresses)}, got {member_count}."
            )
    else:
        if member_count != 0:
            raise RuntimeError(
                "Reputation registry is not in a clean bootstrap state. "
                "Expected zero registered members before bootstrap proposal execution."
            )

        proposer_sender = TransactionSender(w3, voter_accounts["voterA"], gas_price_wei)
        voter_senders = {
            label: TransactionSender(w3, account, gas_price_wei)
            for label, account in voter_accounts.items()
        }
        targets = [reputation_registry.address] * len(voter_addresses)
        values = [0] * len(voter_addresses)
        calldatas = [
            encode_call(reputation_registry, "registerMember", address, INITIAL_MEMBER_REPUTATION)
            for address in voter_addresses.values()
        ]

        execute_governor_proposal(
            w3=w3,
            governor=governor,
            timelock=timelock,
            proposer_sender=proposer_sender,
            voter_senders=voter_senders,
            proposal_record=bootstrap_record,
            targets=targets,
            values=values,
            calldatas=calldatas,
            description=DEMO_BOOTSTRAP_DESCRIPTION,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            persist_callback=persist_callback,
        )

    member_count_after = reputation_registry.functions.memberCount().call()
    total_active_reputation = reputation_registry.functions.totalActiveReputation().call()
    if member_count_after != len(voter_addresses):
        raise RuntimeError(
            f"Bootstrap verification failed: expected {len(voter_addresses)} members, got {member_count_after}."
        )
    if total_active_reputation != len(voter_addresses) * INITIAL_MEMBER_REPUTATION:
        raise RuntimeError(
            "Bootstrap verification failed: total active reputation does not match the configured initial reputation."
        )

    bootstrap_record["snapshots"]["postExecution"] = {
        "members": member_snapshot(reputation_registry, voter_addresses),
        "memberCount": member_count_after,
        "totalActiveReputation": str(total_active_reputation),
    }


def main() -> None:
    args = parse_args()

    w3 = connect_to_sepolia(require_value(args.rpc_url, "rpc-url or SEPOLIA_RPC_URL"))
    deployment_manifest_path = Path(args.deployment_manifest)
    evidence_output_path = Path(args.evidence_output)
    funding_state_output_path = Path(args.funding_state_output)

    deployment_manifest = load_json(deployment_manifest_path)
    contracts = load_required_contracts(w3, deployment_manifest)
    token = contracts["token"]
    reputation = contracts["reputation"]
    hybrid_votes = contracts["hybridVotes"]
    governor = contracts["governor"]
    timelock = contracts["timelock"]
    funding_registry = contracts["fundingRegistry"]
    treasury = contracts["treasury"]
    weth = contracts["weth"]

    project_recipient = to_checksum_address(
        w3,
        require_value(args.project_recipient, "project-recipient or CIF_PROJECT_RECIPIENT"),
        "project-recipient",
    )

    funder_account = parse_account_from_key(require_value(args.funder_private_key, "funder-private-key"))
    voter_accounts = {
        "voterA": parse_account_from_key(require_value(args.voter_a_private_key, "voter-a-private-key")),
        "voterB": parse_account_from_key(require_value(args.voter_b_private_key, "voter-b-private-key")),
        "voterC": parse_account_from_key(require_value(args.voter_c_private_key, "voter-c-private-key")),
    }
    voter_addresses = {label: account.address for label, account in voter_accounts.items()}

    ensure_voter_configuration(deployment_manifest, voter_addresses, token)

    evidence_manifest = load_json(
        evidence_output_path,
        default=build_empty_evidence_manifest(deployment_manifest, project_recipient),
    )
    evidence_manifest["contracts"] = deployment_manifest.get("contracts", {})
    evidence_manifest["participants"] = {
        "funder": funder_account.address,
        **voter_addresses,
    }
    evidence_manifest["project"] = evidence_manifest.get("project") or {}
    evidence_manifest["project"]["name"] = evidence_manifest["project"].get("name") or "Smart Recycling Kiosk"
    evidence_manifest["project"]["projectKey"] = evidence_manifest["project"].get("projectKey") or "SMART_RECYCLING_KIOSK"
    evidence_manifest["project"]["recipient"] = project_recipient

    funder_sender = TransactionSender(w3, funder_account, args.gas_price_wei)

    liquid_before = treasury.functions.liquidWethBalance().call()
    supplied_before = treasury.functions.suppliedWethBalance().call()
    if supplied_before != 0:
        raise RuntimeError(
            f"Treasury already has supplied WETH ({supplied_before}). Seed state must be prepared before proposal execution."
        )
    if liquid_before > DEMO_TREASURY_FUNDING_WETH:
        raise RuntimeError(
            f"Treasury already holds {liquid_before} WETH units, which exceeds the demo starting balance {DEMO_TREASURY_FUNDING_WETH}."
        )

    treasury_top_up = DEMO_TREASURY_FUNDING_WETH - liquid_before
    fund_tx_hash: str | None = None
    if treasury_top_up > 0:
        funder_balance = weth.functions.balanceOf(funder_account.address).call()
        if funder_balance < treasury_top_up:
            raise RuntimeError(
                f"Funder WETH balance {funder_balance} is below the required top-up {treasury_top_up}."
            )
        fund_tx_hash, _ = funder_sender.send_call(weth.functions.transfer(treasury.address, treasury_top_up))

    liquid_after = treasury.functions.liquidWethBalance().call()
    if liquid_after != DEMO_TREASURY_FUNDING_WETH:
        raise RuntimeError(
            f"Treasury liquid WETH mismatch after funding: expected {DEMO_TREASURY_FUNDING_WETH}, got {liquid_after}."
        )

    delegation_transactions: dict[str, Any] = {}
    for label, account in voter_accounts.items():
        current_votes = token.functions.getVotes(account.address).call()
        current_delegate = token.functions.delegates(account.address).call()
        if current_votes == INITIAL_VOTER_ALLOCATION and current_delegate == account.address:
            delegation_transactions[label] = {
                "transactionHash": None,
                "status": "alreadySelfDelegated",
                "address": account.address,
            }
            continue

        if current_votes != 0:
            raise RuntimeError(
                f"{label} already has {current_votes} votes delegated in a non-demo state. Expected 0 or {INITIAL_VOTER_ALLOCATION}."
            )
        if current_delegate not in {ZERO_ADDRESS, account.address}:
            raise RuntimeError(
                f"{label} is already delegated to {current_delegate}. The demo requires self-delegation from a clean state."
            )

        sender = TransactionSender(w3, account, args.gas_price_wei)
        delegation_tx_hash, _ = sender.send_call(token.functions.delegate(account.address))
        votes_after = wait_for_self_delegation(
            token=token,
            address=account.address,
            expected_votes=INITIAL_VOTER_ALLOCATION,
            poll_interval_seconds=max(1.0, min(args.poll_interval_seconds, 5.0)),
            timeout_seconds=min(args.timeout_seconds, 60.0),
        )
        if votes_after != INITIAL_VOTER_ALLOCATION:
            raise RuntimeError(
                f"{label} self-delegation failed: expected {INITIAL_VOTER_ALLOCATION} votes, got {votes_after}."
            )
        delegation_transactions[label] = {
            "transactionHash": delegation_tx_hash,
            "status": "delegated",
            "address": account.address,
        }

    min_liquid_reserve_bps, max_single_grant_bps, stale_price_threshold = treasury.functions.riskPolicy().call()
    if (
        min_liquid_reserve_bps != DEFAULT_MIN_LIQUID_RESERVE_BPS
        or max_single_grant_bps != DEFAULT_MAX_SINGLE_GRANT_BPS
        or stale_price_threshold != DEFAULT_STALE_PRICE_THRESHOLD
    ):
        raise RuntimeError(
            "Treasury risk policy drift detected. "
            f"Expected {(DEFAULT_MIN_LIQUID_RESERVE_BPS, DEFAULT_MAX_SINGLE_GRANT_BPS, DEFAULT_STALE_PRICE_THRESHOLD)}, "
            f"got {(min_liquid_reserve_bps, max_single_grant_bps, stale_price_threshold)}."
        )

    evidence_manifest["seedState"]["fundTreasury"] = {
        "transactionHash": fund_tx_hash,
        "status": "funded" if fund_tx_hash is not None else "alreadyFunded",
        "funder": funder_account.address,
        "deltaWeth": str(treasury_top_up),
        "targetTreasuryLiquidWeth": str(DEMO_TREASURY_FUNDING_WETH),
    }
    evidence_manifest["seedState"]["selfDelegations"] = delegation_transactions

    ensure_members_bootstrapped(
        w3=w3,
        deployment_manifest=deployment_manifest,
        evidence_manifest=evidence_manifest,
        evidence_output_path=evidence_output_path,
        funding_state_output_path=funding_state_output_path,
        voter_accounts=voter_accounts,
        voter_addresses=voter_addresses,
        governor=governor,
        timelock=timelock,
        funding_registry=funding_registry,
        reputation_registry=reputation,
        poll_interval_seconds=args.poll_interval_seconds,
        timeout_seconds=args.timeout_seconds,
        gas_price_wei=args.gas_price_wei,
    )

    evidence_manifest["seedState"]["initialSnapshot"] = {
        "treasury": snapshot_treasury_state(treasury),
        "voters": snapshot_votes(token, voter_addresses, hybrid_votes, reputation),
        "projectRecipientWeth": str(weth.functions.balanceOf(project_recipient).call()),
        "blockNumber": w3.eth.block_number,
        "chainTimestamp": w3.eth.get_block("latest")["timestamp"],
        "memberCount": reputation.functions.memberCount().call(),
        "totalActiveReputation": str(reputation.functions.totalActiveReputation().call()),
        "initialMemberReputation": str(INITIAL_MEMBER_REPUTATION),
        "tokenUnit": str(TOKEN_UNIT),
    }

    persist_outputs(
        deployment_manifest,
        evidence_manifest,
        evidence_output_path,
        funding_state_output_path,
        funding_registry,
        reputation,
    )
    print(f"Seed-state evidence written to {evidence_output_path}")
    print(f"Funding state manifest written to {funding_state_output_path}")


if __name__ == "__main__":
    main()
