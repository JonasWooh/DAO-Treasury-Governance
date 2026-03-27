from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from sepolia_demo_common import (
    DEFAULT_DEPLOYMENT_MANIFEST,
    DEFAULT_EVIDENCE_MANIFEST,
    DEFAULT_EVIDENCE_MARKDOWN,
    DEFAULT_FUNDING_STATE_MANIFEST,
    DEFAULT_SCENARIO_MANIFEST,
    DEFAULT_SCREENSHOT_CHECKLIST,
    etherscan_address_url,
    etherscan_tx_url,
    load_json,
    update_etherscan_links,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Sepolia V2 evidence into report-ready artifacts.")
    parser.add_argument("--deployment-manifest", default=str(DEFAULT_DEPLOYMENT_MANIFEST))
    parser.add_argument("--scenario-manifest", default=str(DEFAULT_SCENARIO_MANIFEST))
    parser.add_argument("--evidence-manifest", default=str(DEFAULT_EVIDENCE_MANIFEST))
    parser.add_argument("--funding-state-manifest", default=str(DEFAULT_FUNDING_STATE_MANIFEST))
    parser.add_argument("--markdown-output", default=str(DEFAULT_EVIDENCE_MARKDOWN))
    parser.add_argument("--screenshot-checklist-output", default=str(DEFAULT_SCREENSHOT_CHECKLIST))
    return parser.parse_args()


def flatten_transaction_rows(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def walk(section: str, prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                walk(section, next_prefix, child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                next_prefix = f"{prefix}.{index}" if prefix else str(index)
                walk(section, next_prefix, child)
        elif isinstance(value, str) and value.startswith("0x") and len(value) == 66:
            rows.append(
                {
                    "section": section,
                    "label": prefix,
                    "txHash": value,
                    "url": etherscan_tx_url(value),
                }
            )

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
    if seed_state.get("fundTreasury", {}).get("transactionHash"):
        tx_hash = seed_state["fundTreasury"]["transactionHash"]
        rows.append(
            {
                "section": "Seed State",
                "label": "fundTreasury",
                "txHash": tx_hash,
                "url": etherscan_tx_url(tx_hash),
            }
        )
    walk("Seed State", "selfDelegations", seed_state.get("selfDelegations", {}))
    walk("Seed State", "bootstrapMembers", seed_state.get("bootstrapMembers", {}).get("transactions", {}))

    for proposal_slug, proposal_record in evidence_manifest.get("proposals", {}).items():
        walk(proposal_slug, "transactions", proposal_record.get("transactions", {}))

    return rows


def render_markdown(
    deployment_manifest: dict[str, Any],
    scenario_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    funding_state_manifest: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Sepolia V2 Demo Evidence")
    lines.append("")
    lines.append(f"- Network: `{deployment_manifest.get('network', {}).get('name', 'sepolia')}`")
    lines.append(f"- Chain ID: `{deployment_manifest.get('network', {}).get('chainId', '')}`")
    lines.append(f"- Funding members: `{len(funding_state_manifest.get('members', []))}`")
    lines.append(f"- Funding proposals: `{len(funding_state_manifest.get('proposals', []))}`")
    lines.append(f"- Active reputation total: `{funding_state_manifest.get('reputationSummary', {}).get('totalActiveReputation', '')}`")
    lines.append(f"- Project ID: `{scenario_manifest.get('project', {}).get('projectId', '')}`")
    lines.append(f"- Project recipient: `{scenario_manifest.get('project', {}).get('recipient', '')}`")
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
    lines.append("## Seed State")
    lines.append("")
    bootstrap = evidence_manifest.get("seedState", {}).get("bootstrapMembers", {})
    lines.append(
        f"- Bootstrap proposal: `{bootstrap.get('proposalId', 'unknown')}` with description hash `{bootstrap.get('descriptionHash', '')}`"
    )
    lines.append(
        f"- Treasury seed target: `{evidence_manifest.get('seedState', {}).get('fundTreasury', {}).get('targetTreasuryLiquidWeth', '')}`"
    )
    lines.append("")
    lines.append("## Funding Workflow Summary")
    lines.append("")
    for proposal in scenario_manifest.get("proposals", []):
        record = evidence_manifest.get("proposals", {}).get(proposal["slug"], {})
        lines.append(f"### {proposal['title']}")
        lines.append("")
        lines.append(f"- Description: `{proposal['description']}`")
        lines.append(f"- Governor proposal ID: `{proposal['proposalId']}`")
        workflow = record.get("workflow", {})
        if workflow.get("fundingProposalId"):
            lines.append(f"- Funding proposal ID: `{workflow['fundingProposalId']}`")
        if workflow.get("projectId"):
            lines.append(f"- Project ID: `{workflow['projectId']}`")
        if workflow.get("milestoneIndex") is not None:
            lines.append(f"- Milestone index: `{workflow['milestoneIndex']}`")
        lines.append(f"- Final state: `{record.get('finalState', 'unknown')}`")
        lines.append("")
    lines.append("## Funding State Snapshot")
    lines.append("")
    for project in funding_state_manifest.get("projects", []):
        lines.append(
            f"- Project `{project['projectId']}` released `{project['releasedWeth']}` / `{project['approvedBudgetWeth']}` WETH, next milestone `{project['nextClaimableMilestone']}`, status `{project['status']}`."
        )
    for member in funding_state_manifest.get("members", []):
        lines.append(
            f"- Member `{member['account']}` active=`{member['isActive']}` reputation=`{member['currentReputation']}`."
        )
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
    lines.append("- Member bootstrap is executed through Governor and Timelock, not through a privileged direct write.")
    lines.append("- Proposal 1 batches FundingRegistry approval and Treasury project activation.")
    lines.append("- Proposal 2 demonstrates idle WETH deployment into Aave without changing funding workflow state.")
    lines.append("- Proposal 3 captures milestone claim execution, Treasury release, and FundingRegistry milestone release.")
    lines.append("- Funding proposal vote participation settlement is exported as a standalone post-Proposal-1 transaction.")
    lines.append("- Milestone claim vote participation settlement is exported as a standalone post-Proposal-3 transaction.")
    lines.append("- The funding_state snapshot records the proposer milestone-release reward and the final settled voter reputation values.")
    lines.append("- Browser screenshots should be captured using the checklist generated alongside this Markdown file.")
    lines.append("")
    return "\n".join(lines)


def render_screenshot_checklist(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    funding_state_manifest: dict[str, Any],
) -> str:
    treasury_address = deployment_manifest.get("contracts", {}).get("InnovationTreasury", "")
    governor_address = deployment_manifest.get("contracts", {}).get("InnovationGovernor", "")
    funding_address = deployment_manifest.get("contracts", {}).get("FundingRegistry", "")
    reputation_address = deployment_manifest.get("contracts", {}).get("ReputationRegistry", "")
    hybrid_address = deployment_manifest.get("contracts", {}).get("HybridVotesAdapter", "")
    recipient_address = evidence_manifest.get("project", {}).get("recipient", "")

    lines: list[str] = []
    lines.append("# Sepolia Screenshot Checklist")
    lines.append("")
    lines.append("- Capture the deployed governance stack pages on Etherscan: token, timelock, governor, reputation registry, hybrid votes adapter.")
    lines.append("- Capture the deployed funding and treasury stack pages on Etherscan: funding registry, treasury, oracle, adapter.")
    lines.append(f"- Capture the FundingRegistry address page: `{funding_address}` ({etherscan_address_url(funding_address) if funding_address else ''}).")
    lines.append(f"- Capture the ReputationRegistry address page: `{reputation_address}` ({etherscan_address_url(reputation_address) if reputation_address else ''}).")
    lines.append(f"- Capture the HybridVotesAdapter address page: `{hybrid_address}` ({etherscan_address_url(hybrid_address) if hybrid_address else ''}).")
    lines.append(f"- Capture the Treasury address page showing holdings: `{treasury_address}` ({etherscan_address_url(treasury_address) if treasury_address else ''}).")
    lines.append(f"- Capture the Governor address page: `{governor_address}` ({etherscan_address_url(governor_address) if governor_address else ''}).")
    lines.append(f"- Capture the project recipient address page before and after Proposal 3: `{recipient_address}` ({etherscan_address_url(recipient_address) if recipient_address else ''}).")
    lines.append("- Capture the three self-delegation transactions and the bootstrap member-registration governance proposal.")
    lines.append("- Capture Proposal 1 funding submission, governor lifecycle, FundingRegistry approved proposal state, and Treasury project activation.")
    lines.append("- Capture Proposal 2 governor lifecycle plus Treasury liquid/supplied WETH state after the Aave deposit.")
    lines.append("- Capture Proposal 1 vote settlement as a standalone transaction after the governor execute step.")
    lines.append("- Capture Proposal 3 claim submission, governor lifecycle, recipient payout, milestone release, milestone reward, and standalone vote settlement transaction.")
    lines.append(f"- Capture the final funding_state snapshot showing `{len(funding_state_manifest.get('projects', []))}` project(s) and `{len(funding_state_manifest.get('members', []))}` member(s).")
    lines.append("- Capture Etherscan verification status pages or maintain a manual verification TODO list for every deployed contract.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    deployment_manifest_path = Path(args.deployment_manifest)
    scenario_manifest_path = Path(args.scenario_manifest)
    evidence_manifest_path = Path(args.evidence_manifest)
    funding_state_manifest_path = Path(args.funding_state_manifest)
    markdown_output_path = Path(args.markdown_output)
    screenshot_checklist_output_path = Path(args.screenshot_checklist_output)

    deployment_manifest = load_json(deployment_manifest_path)
    scenario_manifest = load_json(scenario_manifest_path)
    evidence_manifest = load_json(evidence_manifest_path)
    funding_state_manifest = load_json(funding_state_manifest_path)

    update_etherscan_links(deployment_manifest, evidence_manifest)
    write_json(evidence_manifest_path, evidence_manifest)

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(
        render_markdown(deployment_manifest, scenario_manifest, evidence_manifest, funding_state_manifest),
        encoding="utf-8",
    )

    screenshot_checklist_output_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_checklist_output_path.write_text(
        render_screenshot_checklist(deployment_manifest, evidence_manifest, funding_state_manifest),
        encoding="utf-8",
    )

    print(f"Updated evidence manifest: {evidence_manifest_path}")
    print(f"Markdown evidence written to {markdown_output_path}")
    print(f"Screenshot checklist written to {screenshot_checklist_output_path}")


if __name__ == "__main__":
    main()
