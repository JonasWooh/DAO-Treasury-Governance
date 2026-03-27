from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deliverable_common import (
    DEPLOYMENT_MANIFEST_PATH,
    EVIDENCE_MANIFEST_PATH,
    REPORT_PATH,
    ROOT,
    SCENARIO_MANIFEST_PATH,
    SCREENSHOT_MANIFEST_PATH,
    WORKBOOK_SUMMARY_PATH,
    load_gas_report,
    load_json,
    load_required_manifests,
    load_slither_summary,
    required_screenshot_paths,
)

REFERENCES = [
    ('OpenZeppelin Governance', 'https://docs.openzeppelin.com/contracts/5.x/governance'),
    ('Chainlink Price Feeds', 'https://docs.chain.link/data-feeds/price-feeds/addresses?network=ethereum&page=1#sepolia-testnet'),
    ('Aave Address Book', 'https://github.com/aave-dao/aave-address-book'),
    ('Sepolia Etherscan', 'https://sepolia.etherscan.io'),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate the final PDF report from authoritative Sepolia deliverables.')
    parser.add_argument('--deployment-manifest', default=str(DEPLOYMENT_MANIFEST_PATH))
    parser.add_argument('--scenario-manifest', default=str(SCENARIO_MANIFEST_PATH))
    parser.add_argument('--evidence-manifest', default=str(EVIDENCE_MANIFEST_PATH))
    parser.add_argument('--screenshot-manifest', default=str(SCREENSHOT_MANIFEST_PATH))
    parser.add_argument('--workbook-summary', default=str(WORKBOOK_SUMMARY_PATH))
    parser.add_argument('--output', default=str(REPORT_PATH))
    return parser.parse_args()


def flatten_transaction_rows(deployment_manifest: dict[str, Any], evidence_manifest: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = [['Section', 'Step', 'Transaction Hash']]
    for label, tx_hash in deployment_manifest.get('transactions', {}).items():
        rows.append(['Deployment', label, tx_hash])
    seed_state = evidence_manifest.get('seedState', {})
    fund_treasury = seed_state.get('fundTreasury', {})
    if isinstance(fund_treasury, dict) and fund_treasury.get('transactionHash'):
        rows.append(['Seed State', 'fundTreasury', fund_treasury['transactionHash']])
    self_delegations = seed_state.get('selfDelegations', {})
    if isinstance(self_delegations, dict):
        for voter_label, vote_record in self_delegations.items():
            if isinstance(vote_record, dict) and vote_record.get('transactionHash'):
                rows.append(['Seed State', f'selfDelegate.{voter_label}', vote_record['transactionHash']])
    for proposal_slug, proposal_record in evidence_manifest.get('proposals', {}).items():
        transactions = proposal_record.get('transactions', {}) if isinstance(proposal_record, dict) else {}
        if transactions.get('propose'):
            rows.append([proposal_slug, 'propose', transactions['propose']])
        for voter_label, tx_hash in transactions.get('votes', {}).items():
            if tx_hash:
                rows.append([proposal_slug, f'vote.{voter_label}', tx_hash])
        if transactions.get('queue'):
            rows.append([proposal_slug, 'queue', transactions['queue']])
        if transactions.get('execute'):
            rows.append([proposal_slug, 'execute', transactions['execute']])
    return rows


def build_artifact_index(output_path: Path) -> list[list[str]]:
    return [
        ['Artifact', 'Path'],
        ['Deployment manifest', str(DEPLOYMENT_MANIFEST_PATH)],
        ['Proposal scenario manifest', str(SCENARIO_MANIFEST_PATH)],
        ['Demo evidence manifest', str(EVIDENCE_MANIFEST_PATH)],
        ['Screenshot manifest', str(SCREENSHOT_MANIFEST_PATH)],
        ['Workbook summary', str(WORKBOOK_SUMMARY_PATH)],
        ['Final PDF report', str(output_path)],
    ]


def add_section_heading(story: list[Any], title: str, styles) -> None:
    story.append(Paragraph(title, styles['Heading1']))
    story.append(Spacer(1, 0.18 * inch))


def add_table(story: list[Any], rows: list[list[str]], column_widths=None) -> None:
    table = Table(rows, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a3b42')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cdbfa8')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f4ecdf')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('LEADING', (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))


def build_story(
    deployment_manifest: dict[str, Any],
    scenario_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
    screenshot_manifest: dict[str, Any],
    workbook_summary: dict[str, Any],
    gas_report: dict[str, Any],
    slither_summary: dict[str, Any],
    output_path: Path,
) -> list[Any]:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyTight', parent=styles['BodyText'], leading=16, spaceAfter=8))
    story: list[Any] = []

    story.append(Paragraph('Campus Innovation Fund DAO', styles['Title']))
    story.append(Paragraph('First-Pass Final Report for the Industrial-Quality DAO Prototype on Sepolia', styles['Heading2']))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph('1. Title page', styles['Heading1']))
    story.append(Paragraph('This report packages the governance, treasury, Oracle, Aave integration, frontend, and evidence deliverables for the Sepolia prototype.', styles['BodyTight']))
    story.append(PageBreak())

    add_section_heading(story, '2. Objective and project description', styles)
    story.append(Paragraph('The objective was to implement a constrained DAO treasury for a campus innovation fund, with delegated voting, timelocked execution, staged project release, and explicit NAV reporting.', styles['BodyTight']))
    add_section_heading(story, '3. Why we chose this project and what we expected', styles)
    story.append(Paragraph('The project was chosen because it combines practical governance, operational treasury constraints, and externally verifiable protocol integrations. We expected the prototype to demonstrate policy-enforced capital deployment rather than arbitrary contract administration.', styles['BodyTight']))
    add_section_heading(story, '4. Business use case', styles)
    story.append(Paragraph('A campus innovation fund has recurring pressure to approve projects, hold working capital, release funds by milestone, and preserve liquidity. The DAO implementation turns those operating rules into on-chain constraints.', styles['BodyTight']))
    add_section_heading(story, '5. System architecture and governance flow', styles)
    story.append(Paragraph('The production path is Token -> Governor -> Timelock -> Treasury -> Aave / Project Recipient. Proposal 3 demonstrates a two-action execution path that withdraws idle funds from Aave and releases a milestone payment in a single governance action.', styles['BodyTight']))
    add_section_heading(story, '6. Contract design and security controls', styles)
    story.append(Paragraph('Treasury operations are timelock-owned. The Treasury does not expose rescue paths, arbitrary call execution, hidden auto-withdraw behavior, or silent fallback logic. Oracle staleness is checked explicitly. Adapter flows reconcile exact before/after balances.', styles['BodyTight']))
    add_section_heading(story, '7. Testing and methodology', styles)
    story.append(Paragraph('The project includes governance lifecycle, treasury, oracle, adapter, and failure-path tests. Required negative paths include direct EOA treasury calls, premature timelock execution, over-budget milestone release, stale oracle data, and reserve-floor breaches on Aave deposits.', styles['BodyTight']))
    gas_rows = [['Function', 'Baseline', 'Optimized', 'Delta']] + [[name, str(gas_report['baseline'][name]), str(gas_report['optimized'][name]), str(gas_report['delta'][name])] for name in gas_report['baseline']]
    add_table(story, gas_rows, column_widths=[1.9 * inch, 1.0 * inch, 1.0 * inch, 0.8 * inch])
    add_section_heading(story, '8. Advanced functionality', styles)
    story.append(Paragraph('Advanced functionality includes Chainlink ETH / USD valuation, Aave V3 idle-fund supply and withdrawal, proposal-controlled project approval, and strict milestone sequencing.', styles['BodyTight']))
    slither_rows = [['Target', 'Production detectors']]
    for result in slither_summary.get('results', []):
        slither_rows.append([str(result.get('target', 'unknown')), str(result.get('productionDetectorCount', 0))])
    add_table(story, slither_rows, column_widths=[4.7 * inch, 1.4 * inch])
    add_section_heading(story, '9. Sepolia deployment and evidence', styles)
    story.append(Paragraph(f"Network: {deployment_manifest['network']['name']} ({deployment_manifest['network']['chainId']}).", styles['BodyTight']))
    address_rows = [['Name', 'Address']]
    for name, address in deployment_manifest['contracts'].items():
        address_rows.append([name, address])
    for name, address in deployment_manifest['externalProtocols'].items():
        address_rows.append([name, address])
    add_table(story, address_rows, column_widths=[2.3 * inch, 4.1 * inch])
    add_section_heading(story, '10. Excel treasury analysis', styles)
    story.append(Paragraph(f"Workbook start state: {workbook_summary['startingState']['totalManagedWeth']} total WETH, {workbook_summary['startingState']['liquidWeth']} liquid WETH, {workbook_summary['startingState']['suppliedWeth']} supplied WETH, ETH baseline {workbook_summary['startingState']['ethPriceUsd']} USD.", styles['BodyTight']))
    analysis_rows = [['Metric', 'Value'], ['Scenario count', str(workbook_summary['scenarioCount'])], ['Worst-case scenario', f"{workbook_summary['worstCase']['scenario']} -> {workbook_summary['worstCase']['navUsd']} USD"], ['Best-case scenario', f"{workbook_summary['bestCase']['scenario']} -> {workbook_summary['bestCase']['navUsd']} USD"]]
    add_table(story, analysis_rows, column_widths=[2.3 * inch, 4.1 * inch])
    add_section_heading(story, '11. Step-by-step summary of what we did', styles)
    story.append(Paragraph('1. Deployed the governance spine. 2. Deployed the treasury stack. 3. Seeded Treasury with 5 WETH and activated self-delegation. 4. Executed three complete governance proposals. 5. Exported evidence manifests. 6. Generated frontend, workbook, and report deliverables.', styles['BodyTight']))
    add_section_heading(story, '12. What we learned', styles)
    story.append(Paragraph('The most important lesson is that governance demonstrations are strongest when operational rules are encoded as explicit invariants rather than informal off-chain process. The treasury and adapter layers needed exact balance reconciliation to avoid ambiguity.', styles['BodyTight']))
    add_section_heading(story, '13. References', styles)
    reference_rows = [['Reference', 'URL']] + [[label, url] for label, url in REFERENCES]
    add_table(story, reference_rows, column_widths=[2.0 * inch, 4.4 * inch])
    add_section_heading(story, '14. Appendix with addresses, tx hashes, and artifact index', styles)
    add_table(story, flatten_transaction_rows(deployment_manifest, evidence_manifest), column_widths=[1.5 * inch, 1.7 * inch, 3.4 * inch])
    add_table(story, build_artifact_index(output_path), column_widths=[2.1 * inch, 4.3 * inch])

    for entry in screenshot_manifest['screenshots']:
        image_path = ROOT / entry['expectedPath'] if not Path(entry['expectedPath']).is_absolute() else Path(entry['expectedPath'])
        story.append(Paragraph(f"Screenshot Appendix: {entry['caption']}", styles['Heading3']))
        story.append(Paragraph(f"Path: {image_path}", styles['BodyTight']))
        story.append(Image(str(image_path), width=6.1 * inch, height=3.4 * inch))
        story.append(Spacer(1, 0.18 * inch))

    return story


def main() -> None:
    args = parse_args()
    manifests = load_required_manifests(Path(args.deployment_manifest), Path(args.scenario_manifest), Path(args.evidence_manifest), Path(args.screenshot_manifest))
    workbook_summary = load_json(Path(args.workbook_summary))
    gas_report = load_gas_report()
    slither_summary = load_slither_summary()
    output_path = Path(args.output)

    missing_required = [path for path in required_screenshot_paths(manifests['screenshot']) if not path.exists()]
    if missing_required:
        missing_string = '\n'.join(str(path) for path in missing_required)
        raise FileNotFoundError(f'Required screenshots are missing:\n{missing_string}')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=42)
    story = build_story(manifests['deployment'], manifests['scenario'], manifests['evidence'], manifests['screenshot'], workbook_summary, gas_report, slither_summary, output_path)
    document.build(story)
    print(f'Final report written to {output_path}')


if __name__ == '__main__':
    main()
