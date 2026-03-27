from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any

from deliverable_common import (
    ANALYSIS_DIR,
    DEPLOYMENT_MANIFEST_PATH,
    EVIDENCE_MANIFEST_PATH,
    FUNDING_STATE_PATH,
    FRONTEND_ABI_DIR,
    FRONTEND_CONFIG_PATH,
    FRONTEND_DIR,
    REPORT_PATH,
    SCENARIO_MANIFEST_PATH,
    SCREENSHOT_MANIFEST_PATH,
    WORKBOOK_PATH,
    is_address,
    load_json,
    load_required_manifests,
    required_screenshot_paths,
)

REQUIRED_FRONTEND_ABIS = [
    'CampusInnovationFundToken',
    'ReputationRegistry',
    'HybridVotesAdapter',
    'InnovationGovernor',
    'FundingRegistry',
    'InnovationTreasury',
    'TreasuryOracle',
    'AaveWethAdapter',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate the complete Milestone 6-7 submission package.')
    parser.add_argument('--deployment-manifest', default=str(DEPLOYMENT_MANIFEST_PATH))
    parser.add_argument('--scenario-manifest', default=str(SCENARIO_MANIFEST_PATH))
    parser.add_argument('--evidence-manifest', default=str(EVIDENCE_MANIFEST_PATH))
    parser.add_argument('--funding-state-manifest', default=str(FUNDING_STATE_PATH))
    parser.add_argument('--screenshot-manifest', default=str(SCREENSHOT_MANIFEST_PATH))
    parser.add_argument('--skip-frontend-build', action='store_true')
    parser.add_argument('--frontend-dir', default=str(FRONTEND_DIR))
    parser.add_argument('--frontend-config', default=str(FRONTEND_CONFIG_PATH))
    parser.add_argument('--report', default=str(REPORT_PATH))
    parser.add_argument('--workbook', default=str(WORKBOOK_PATH))
    return parser.parse_args()


def validate_frontend_bundle(frontend_config_path: Path) -> None:
    config = load_json(frontend_config_path)
    if config.get('network', {}).get('chainId') != 11155111:
        raise ValueError('Frontend config must target Sepolia (11155111).')
    if not config.get('configured'):
        raise ValueError('Frontend config is not marked as configured. Run scripts/export_frontend_bundle.py first.')
    for name in REQUIRED_FRONTEND_ABIS:
        address = config.get('contracts', {}).get(name)
        if not is_address(address):
            raise ValueError(f'Frontend config contract {name} is not a valid address.')
    if not config.get('evidenceSources', {}).get('fundingState'):
        raise ValueError('Frontend config is missing evidenceSources.fundingState.')
    for name in REQUIRED_FRONTEND_ABIS:
        abi_path = FRONTEND_ABI_DIR / f'{name}.json'
        payload = load_json(abi_path)
        if 'abi' not in payload or not isinstance(payload['abi'], list):
            raise ValueError(f'Frontend ABI bundle is malformed: {abi_path}')


def validate_manifest_consistency(manifests: dict[str, dict[str, Any]]) -> None:
    deployment_manifest = manifests['deployment']
    scenario_manifest = manifests['scenario']
    evidence_manifest = manifests['evidence']

    if evidence_manifest.get('project', {}).get('recipient') != scenario_manifest.get('project', {}).get('recipient'):
        raise ValueError('Evidence manifest project recipient does not match the scenario manifest project recipient.')

    scenario_proposals = {proposal['slug']: proposal for proposal in scenario_manifest.get('proposals', [])}
    evidence_proposals = evidence_manifest.get('proposals', {})
    for slug, proposal in scenario_proposals.items():
        if slug not in evidence_proposals:
            raise ValueError(f'Evidence manifest is missing proposal record for {slug}.')
        record = evidence_proposals[slug]
        if record.get('proposalId') != proposal.get('proposalId'):
            raise ValueError(f'Proposal ID mismatch for {slug}.')
        transactions = record.get('transactions', {})
        for required_step in ('propose', 'queue', 'execute'):
            if not transactions.get(required_step):
                raise ValueError(f'Evidence manifest is missing {slug}.{required_step} transaction hash.')

    if evidence_manifest.get('contracts') and evidence_manifest['contracts'] != deployment_manifest['contracts']:
        raise ValueError('Evidence manifest contracts map does not match deployment manifest contracts map.')


def validate_required_artifacts(report_path: Path, workbook_path: Path, screenshot_paths: list[Path]) -> None:
    if not workbook_path.exists():
        raise FileNotFoundError(f'Missing workbook: {workbook_path}')
    if not report_path.exists():
        raise FileNotFoundError(f'Missing report PDF: {report_path}')
    missing_screenshots = [path for path in screenshot_paths if not path.exists()]
    if missing_screenshots:
        missing_string = '\n'.join(str(path) for path in missing_screenshots)
        raise FileNotFoundError(f'Required screenshots are missing:\n{missing_string}')

    gas_report = ANALYSIS_DIR / 'gas' / 'gas-report.json'
    slither_summary = ANALYSIS_DIR / 'static' / 'slither-summary.json'
    if not gas_report.exists():
        raise FileNotFoundError(f'Missing gas report: {gas_report}')
    if not slither_summary.exists():
        raise FileNotFoundError(f'Missing Slither summary: {slither_summary}')


def run_frontend_build(frontend_dir: Path) -> None:
    npm_command = shutil.which('npm.cmd') or shutil.which('npm')
    if npm_command is None:
        raise FileNotFoundError('Unable to find npm or npm.cmd on PATH. Activate the conda environment before validation.')
    completed = subprocess.run([npm_command, '--prefix', str(frontend_dir), 'run', 'build'], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError('Frontend build failed during submission validation.\n' f'STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}')


def main() -> None:
    args = parse_args()
    manifests = load_required_manifests(
        Path(args.deployment_manifest),
        Path(args.scenario_manifest),
        Path(args.evidence_manifest),
        Path(args.funding_state_manifest),
        Path(args.screenshot_manifest),
    )
    validate_frontend_bundle(Path(args.frontend_config))
    validate_manifest_consistency(manifests)
    validate_required_artifacts(Path(args.report), Path(args.workbook), required_screenshot_paths(manifests['screenshot']))

    artifact_index = [Path(args.frontend_config), Path(args.report), Path(args.workbook)]
    for artifact_path in artifact_index:
        if not artifact_path.exists():
            raise FileNotFoundError(f'Artifact index entry does not exist: {artifact_path}')

    if not args.skip_frontend_build:
        run_frontend_build(Path(args.frontend_dir))

    print('Submission package validation completed successfully.')


if __name__ == '__main__':
    main()
