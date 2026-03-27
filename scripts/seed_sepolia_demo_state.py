from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from web3 import Web3

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEMO_TREASURY_FUNDING_WETH,
    INITIAL_VOTER_ALLOCATION,
    PROJECT_ID,
    TOKEN_UNIT,
    ZERO_ADDRESS,
    TransactionSender,
    build_empty_evidence_manifest,
    connect_to_sepolia,
    env_default,
    load_json,
    load_required_contracts,
    parse_account_from_key,
    require_value,
    snapshot_treasury_state,
    snapshot_votes,
    to_checksum_address,
    update_etherscan_links,
    write_json,
)

DEFAULT_MIN_LIQUID_RESERVE_BPS = 3000
DEFAULT_MAX_SINGLE_GRANT_BPS = 2000
DEFAULT_STALE_PRICE_THRESHOLD = 3600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the Sepolia demo state for Milestone 5.")
    parser.add_argument("--rpc-url", default=env_default("SEPOLIA_RPC_URL"))
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--evidence-output", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--project-recipient", default=env_default("CIF_PROJECT_RECIPIENT"))
    parser.add_argument("--funder-private-key", default=env_default("CIF_TREASURY_FUNDER_PRIVATE_KEY"))
    parser.add_argument("--voter-a-private-key", default=env_default("CIF_VOTER_A_PRIVATE_KEY"))
    parser.add_argument("--voter-b-private-key", default=env_default("CIF_VOTER_B_PRIVATE_KEY"))
    parser.add_argument("--voter-c-private-key", default=env_default("CIF_VOTER_C_PRIVATE_KEY"))
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


def main() -> None:
    args = parse_args()

    w3 = connect_to_sepolia(require_value(args.rpc_url, "rpc-url or SEPOLIA_RPC_URL"))
    deployment_manifest_path = Path(args.deployment_manifest)
    evidence_output_path = Path(args.evidence_output)

    deployment_manifest = load_json(deployment_manifest_path)
    contracts = load_required_contracts(w3, deployment_manifest)
    token = contracts["token"]
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
    existing_project_recipient = evidence_manifest.get("project", {}).get("recipient")
    if existing_project_recipient is not None:
        existing_project_recipient = to_checksum_address(w3, existing_project_recipient, "existing project recipient")
        if existing_project_recipient != project_recipient:
            raise RuntimeError(
                f"Evidence manifest already records project recipient {existing_project_recipient}, not {project_recipient}."
            )
    evidence_manifest["contracts"] = deployment_manifest.get("contracts", {})
    evidence_manifest["participants"] = {
        "funder": funder_account.address,
        **voter_addresses,
    }
    evidence_manifest["project"] = evidence_manifest.get("project") or {
        "projectId": PROJECT_ID,
        "recipient": project_recipient,
    }
    evidence_manifest["project"]["projectId"] = PROJECT_ID
    evidence_manifest["project"]["recipient"] = project_recipient

    funder_sender = TransactionSender(w3, funder_account, args.gas_price_wei)

    liquid_before = treasury.functions.liquidWethBalance().call()
    supplied_before = treasury.functions.suppliedWethBalance().call()
    project_used = treasury.functions.projectIdUsed(Web3.to_bytes(hexstr=PROJECT_ID)).call()

    if supplied_before != 0:
        raise RuntimeError(
            f"Treasury already has supplied WETH ({supplied_before}). Seed state must be prepared before proposal execution."
        )
    if project_used:
        raise RuntimeError("Smart Recycling Kiosk project is already registered. Seed state must be prepared before proposal 1.")
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
        votes_after = token.functions.getVotes(account.address).call()
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

    evidence_manifest["seedState"] = {
        "fundTreasury": {
            "transactionHash": fund_tx_hash,
            "status": "funded" if fund_tx_hash is not None else "alreadyFunded",
            "funder": funder_account.address,
            "deltaWeth": str(treasury_top_up),
            "targetTreasuryLiquidWeth": str(DEMO_TREASURY_FUNDING_WETH),
        },
        "selfDelegations": delegation_transactions,
        "initialSnapshot": {
            "treasury": snapshot_treasury_state(treasury),
            "voters": snapshot_votes(token, voter_addresses),
            "projectRecipientWeth": str(weth.functions.balanceOf(project_recipient).call()),
            "blockNumber": w3.eth.block_number,
            "chainTimestamp": w3.eth.get_block("latest")["timestamp"],
        },
    }

    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_output_path, evidence_manifest)
    print(f"Seed-state evidence written to {evidence_output_path}")


if __name__ == "__main__":
    main()