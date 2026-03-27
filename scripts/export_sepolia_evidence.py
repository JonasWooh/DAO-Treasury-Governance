from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_EVIDENCE_MARKDOWN,
    DEFAULT_SCENARIO_MANIFEST,
    DEFAULT_SCREENSHOT_CHECKLIST,
    etherscan_address_url,
    etherscan_tx_url,
    load_json,
    update_etherscan_links,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Milestone 5 Sepolia evidence into report-ready artifacts.")
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--scenario-manifest", default=str(DEFAULT_SCENARIO_MANIFEST))
    parser.add_argument("--evidence-manifest", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--markdown-output", default=str(DEFAULT_EVIDENCE_MARKDOWN))
    parser.add_argument("--screenshot-checklist-output", default=str(DEFAULT_SCREENSHOT_CHECKLIST))
    return parser.parse_args()


def flatten_transaction_rows(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for label, tx_hash in deployment_manifest.get("transactions", {}).items():
        rows.append(
            {
                "section": "Deployment",
                "label": label,
                "txHash": tx_hash,
                "url": etherscan_tx_url(tx_hash),
            }
        )

    seed_state = evidence_manifest.get("seedState", {})
    fund_treasury = seed_state.get("fundTreasury", {})
    if fund_treasury.get("transactionHash"):
        rows.append(
            {
                "section": "Seed State",
                "label": "fundTreasury",
                "txHash": fund_treasury["transactionHash"],
                "url": etherscan_tx_url(fund_treasury["transactionHash"]),
            }
        )

    for voter_label, vote_record in seed_state.get("selfDelegations", {}).items():
        tx_hash = vote_record.get("transactionHash")
        if tx_hash is None:
            continue
        rows.append(
            {
                "section": "Seed State",
                "label": f"selfDelegate.{voter_label}",
                "txHash": tx_hash,
                "url": etherscan_tx_url(tx_hash),
            }
        )

    for proposal_slug, proposal_record in evidence_manifest.get("proposals", {}).items():
        transactions = proposal_record.get("transactions", {})
        if transactions.get("propose"):
            rows.append(
                {
                    "section": proposal_slug,
                    "label": "propose",
                    "txHash": transactions["propose"],
                    "url": etherscan_tx_url(transactions["propose"]),
                }
            )
        for voter_label, tx_hash in transactions.get("votes", {}).items():
            if tx_hash is None:
                continue
            rows.append(
                {
                    "section": proposal_slug,
                    "label": f"vote.{voter_label}",
                    "txHash": tx_hash,
                    "url": etherscan_tx_url(tx_hash),
                }
            )
        if transactions.get("queue"):
            rows.append(
                {
                    "section": proposal_slug,
                    "label": "queue",
                    "txHash": transactions["queue"],
                    "url": etherscan_tx_url(transactions["queue"]),
                }
            )
        if transactions.get("execute"):
            rows.append(
                {
                    "section": proposal_slug,
                    "label": "execute",
                    "txHash": transactions["execute"],
                    "url": etherscan_tx_url(transactions["execute"]),
                }
            )

    return rows


def render_markdown(
    deployment_manifest: dict[str, Any],
    scenario_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Milestone 5 Sepolia Evidence")
    lines.append("")
    lines.append(f"- Network: `{deployment_manifest.get('network', {}).get('name', 'sepolia')}`")
    lines.append(f"- Chain ID: `{deployment_manifest.get('network', {}).get('chainId', '')}`")
    lines.append(f"- Project ID: `{evidence_manifest.get('project', {}).get('projectId', '')}`")
    lines.append(f"- Project recipient: `{evidence_manifest.get('project', {}).get('recipient', '')}`")
    lines.append("")
    lines.append("## Contract Addresses")
    lines.append("")
    lines.append("| Name | Address | Etherscan |")
    lines.append("| --- | --- | --- |")
    for name, address in deployment_manifest.get("contracts", {}).items():
        lines.append(f"| {name} | `{address}` | [link]({etherscan_address_url(address)}) |")
    for name, address in deployment_manifest.get("externalProtocols", {}).items():
        lines.append(f"| {name} | `{address}` | [link]({etherscan_address_url(address)}) |")
    lines.append("")
    lines.append("## Proposal Summary")
    lines.append("")
    for proposal in scenario_manifest.get("proposals", []):
        record = evidence_manifest.get("proposals", {}).get(proposal["slug"], {})
        lines.append(f"### {proposal['title']}")
        lines.append("")
        lines.append(f"- Description: `{proposal['description']}`")
        lines.append(f"- Proposal ID: `{proposal['proposalId']}`")
        lines.append(f"- Operation ID: `{proposal['operationId']}`")
        lines.append(f"- Final state: `{record.get('finalState', 'unknown')}`")
        lines.append("")
    lines.append("## Transaction Hash Table")
    lines.append("")
    lines.append("| Section | Step | Transaction Hash | Etherscan |")
    lines.append("| --- | --- | --- | --- |")
    for row in flatten_transaction_rows(deployment_manifest, evidence_manifest):
        lines.append(f"| {row['section']} | {row['label']} | `{row['txHash']}` | [link]({row['url']}) |")
    lines.append("")
    lines.append("## Manual Verification Notes")
    lines.append("")
    lines.append("- Etherscan contract verification remains a manual or semi-automated follow-up step in this first Milestone 5 automation pass.")
    lines.append("- Browser screenshots should be captured using the checklist generated alongside this Markdown file.")
    lines.append("- Proposal 3 is expected to be a single proposal with two actions: Aave withdrawal and milestone release.")
    lines.append("")
    return "\n".join(lines)


def render_screenshot_checklist(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> str:
    treasury_address = deployment_manifest.get("contracts", {}).get("InnovationTreasury", "")
    governor_address = deployment_manifest.get("contracts", {}).get("InnovationGovernor", "")
    recipient_address = evidence_manifest.get("project", {}).get("recipient", "")

    lines: list[str] = []
    lines.append("# Sepolia Screenshot Checklist")
    lines.append("")
    lines.append("- Capture the deployed governance contract pages on Etherscan: token, timelock, governor.")
    lines.append("- Capture the deployed treasury stack pages on Etherscan: treasury, oracle, adapter.")
    lines.append(f"- Capture the Treasury address page showing holdings: `{treasury_address}` ({etherscan_address_url(treasury_address) if treasury_address else ''}).")
    lines.append(f"- Capture the Governor address page: `{governor_address}` ({etherscan_address_url(governor_address) if governor_address else ''}).")
    lines.append(f"- Capture the project recipient address page before and after Proposal 3: `{recipient_address}` ({etherscan_address_url(recipient_address) if recipient_address else ''}).")
    lines.append("- Capture the three self-delegation transactions from the seed state.")
    lines.append("- Capture Proposal 1: propose, votes, queue, execute, and the approved project state.")
    lines.append("- Capture Proposal 2: propose, votes, queue, execute, and the Treasury liquid/supplied WETH state.")
    lines.append("- Capture Proposal 3: propose, votes, queue, execute, plus the recipient payout and project milestone release.")
    lines.append("- Capture the final Treasury NAV / balances used in the report tables.")
    lines.append("- Capture Etherscan verification status pages or maintain a manual verification TODO list for every deployed contract.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    deployment_manifest_path = Path(args.deployment_manifest)
    scenario_manifest_path = Path(args.scenario_manifest)
    evidence_manifest_path = Path(args.evidence_manifest)
    markdown_output_path = Path(args.markdown_output)
    screenshot_checklist_output_path = Path(args.screenshot_checklist_output)

    deployment_manifest = load_json(deployment_manifest_path)
    scenario_manifest = load_json(scenario_manifest_path)
    evidence_manifest = load_json(evidence_manifest_path)

    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_manifest_path, evidence_manifest)

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(
        render_markdown(deployment_manifest, scenario_manifest, evidence_manifest),
        encoding="utf-8",
    )

    screenshot_checklist_output_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_checklist_output_path.write_text(
        render_screenshot_checklist(deployment_manifest, evidence_manifest),
        encoding="utf-8",
    )

    print(f"Updated evidence manifest: {evidence_manifest_path}")
    print(f"Markdown evidence written to {markdown_output_path}")
    print(f"Screenshot checklist written to {screenshot_checklist_output_path}")


if __name__ == "__main__":
    main()