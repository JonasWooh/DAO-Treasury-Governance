from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / 'frontend'
FRONTEND_GENERATED_DIR = FRONTEND_DIR / 'src' / 'generated'
FRONTEND_ABI_DIR = FRONTEND_GENERATED_DIR / 'abi'
FRONTEND_RUNTIME_DIR = FRONTEND_DIR / 'public' / 'runtime'
DEPLOYMENTS_DIR = ROOT / 'deployments'
EVIDENCE_DIR = ROOT / 'evidence' / 'screenshots'
EXCEL_DIR = ROOT / 'excel'
REPORTS_DIR = ROOT / 'reports'
ANALYSIS_DIR = ROOT / 'analysis'

DEPLOYMENT_MANIFEST_PATH = DEPLOYMENTS_DIR / 'deployments.sepolia.json'
SCENARIO_MANIFEST_PATH = DEPLOYMENTS_DIR / 'proposal_scenarios.sepolia.json'
EVIDENCE_MANIFEST_PATH = DEPLOYMENTS_DIR / 'demo_evidence.sepolia.json'
SCREENSHOT_MANIFEST_PATH = EVIDENCE_DIR / 'screenshot-manifest.sepolia.json'
WORKBOOK_PATH = EXCEL_DIR / 'treasury_analysis.sepolia.xlsx'
WORKBOOK_SUMMARY_PATH = EXCEL_DIR / 'treasury_analysis.sepolia.summary.json'
REPORT_PATH = REPORTS_DIR / 'final_report.sepolia.pdf'
FRONTEND_CONFIG_PATH = FRONTEND_GENERATED_DIR / 'frontend.config.sepolia.json'

SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_NETWORK_NAME = 'sepolia'
SEPOLIA_ETHERSCAN_BASE_URL = 'https://sepolia.etherscan.io'

REQUIRED_CONTRACT_NAMES = [
    'CampusInnovationFundToken',
    'InnovationGovernor',
    'TimelockController',
    'InnovationTreasury',
    'TreasuryOracle',
    'AaveWethAdapter',
]

REQUIRED_EXTERNAL_PROTOCOL_NAMES = [
    'WETH',
    'ChainlinkEthUsdFeed',
    'AavePool',
    'AaveAWeth',
]

FRONTEND_ABI_ARTIFACTS = {
    'CampusInnovationFundToken': ROOT / 'artifacts' / 'src' / 'governance' / 'CampusInnovationFundToken' / 'CampusInnovationFundToken.json',
    'InnovationGovernor': ROOT / 'artifacts' / 'src' / 'governance' / 'InnovationGovernor' / 'InnovationGovernor.json',
    'InnovationTreasury': ROOT / 'artifacts' / 'src' / 'treasury' / 'InnovationTreasury' / 'InnovationTreasury.json',
    'TreasuryOracle': ROOT / 'artifacts' / 'src' / 'oracle' / 'TreasuryOracle' / 'TreasuryOracle.json',
    'AaveWethAdapter': ROOT / 'artifacts' / 'src' / 'adapters' / 'AaveWethAdapter' / 'AaveWethAdapter.json',
}


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f'Missing required file: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f'{label} must be a JSON object.')
    return value


def is_address(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 42 and value.startswith('0x')


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 66 and value.startswith('0x')


def validate_sepolia_network(manifest: dict[str, Any], label: str) -> None:
    network = require_object(manifest.get('network'), f'{label}.network')
    if network.get('name') != SEPOLIA_NETWORK_NAME or network.get('chainId') != SEPOLIA_CHAIN_ID:
        raise ValueError(f'{label} must target Sepolia ({SEPOLIA_CHAIN_ID}).')


def validate_deployment_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_sepolia_network(manifest, 'deployment manifest')
    contracts = require_object(manifest.get('contracts'), 'deployment manifest.contracts')
    external_protocols = require_object(manifest.get('externalProtocols'), 'deployment manifest.externalProtocols')
    for name in REQUIRED_CONTRACT_NAMES:
        if not is_address(contracts.get(name)):
            raise ValueError(f'deployment manifest is missing a valid address for contracts.{name}')
    for name in REQUIRED_EXTERNAL_PROTOCOL_NAMES:
        if not is_address(external_protocols.get(name)):
            raise ValueError(f'deployment manifest is missing a valid address for externalProtocols.{name}')
    return manifest


def validate_scenario_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    project = require_object(manifest.get('project'), 'scenario manifest.project')
    if not is_hash(project.get('projectId')):
        raise ValueError('scenario manifest.project.projectId must be a bytes32 hash string')
    if not is_address(project.get('recipient')):
        raise ValueError('scenario manifest.project.recipient must be an address')

    proposals = manifest.get('proposals')
    if not isinstance(proposals, list) or len(proposals) == 0:
        raise ValueError('scenario manifest.proposals must be a non-empty list')
    for proposal in proposals:
        entry = require_object(proposal, 'scenario manifest.proposals[]')
        if not is_hash(entry.get('descriptionHash')) or not is_hash(entry.get('operationId')):
            raise ValueError('scenario manifest contains a malformed proposal hash field')
        targets = entry.get('targets')
        if not isinstance(targets, list) or any(not is_address(target) for target in targets):
            raise ValueError('scenario manifest contains an invalid proposal target address')
    return manifest


def validate_evidence_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_sepolia_network(manifest, 'evidence manifest')
    require_object(manifest.get('participants'), 'evidence manifest.participants')
    require_object(manifest.get('seedState'), 'evidence manifest.seedState')
    require_object(manifest.get('proposals'), 'evidence manifest.proposals')
    etherscan_links = require_object(manifest.get('etherscanLinks'), 'evidence manifest.etherscanLinks')
    require_object(etherscan_links.get('addresses'), 'evidence manifest.etherscanLinks.addresses')
    require_object(etherscan_links.get('transactions'), 'evidence manifest.etherscanLinks.transactions')
    return manifest


def validate_screenshot_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_sepolia_network(manifest, 'screenshot manifest')
    screenshots = manifest.get('screenshots')
    if not isinstance(screenshots, list) or len(screenshots) == 0:
        raise ValueError('screenshot manifest.screenshots must be a non-empty list')
    for screenshot in screenshots:
        entry = require_object(screenshot, 'screenshot manifest entry')
        for key in ('id', 'caption', 'reportSection', 'expectedPath', 'category'):
            if not isinstance(entry.get(key), str) or entry.get(key) == '':
                raise ValueError(f'screenshot manifest entry is missing string field {key}')
        if not isinstance(entry.get('required'), bool):
            raise ValueError('screenshot manifest entry.required must be boolean')
    return manifest


def load_required_manifests(
    deployment_path: Path = DEPLOYMENT_MANIFEST_PATH,
    scenario_path: Path = SCENARIO_MANIFEST_PATH,
    evidence_path: Path = EVIDENCE_MANIFEST_PATH,
    screenshot_path: Path = SCREENSHOT_MANIFEST_PATH,
) -> dict[str, dict[str, Any]]:
    deployment_manifest = validate_deployment_manifest(load_json(deployment_path))
    scenario_manifest = validate_scenario_manifest(load_json(scenario_path))
    evidence_manifest = validate_evidence_manifest(load_json(evidence_path))
    screenshot_manifest = validate_screenshot_manifest(load_json(screenshot_path))
    return {
        'deployment': deployment_manifest,
        'scenario': scenario_manifest,
        'evidence': evidence_manifest,
        'screenshot': screenshot_manifest,
    }


def export_frontend_config_payload(deployment_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        'generatedAt': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'configured': True,
        'network': deployment_manifest['network'],
        'contracts': {name: deployment_manifest['contracts'][name] for name in REQUIRED_CONTRACT_NAMES},
        'externalProtocols': {
            'WETH': deployment_manifest['externalProtocols']['WETH'],
            'ChainlinkEthUsdFeed': deployment_manifest['externalProtocols']['ChainlinkEthUsdFeed'],
            'AavePool': deployment_manifest['externalProtocols']['AavePool'],
            'AaveAWeth': deployment_manifest['externalProtocols']['AaveAWeth'],
        },
        'evidenceSources': {
            'deployments': '/runtime/deployments.sepolia.json',
            'proposalScenarios': '/runtime/proposal_scenarios.sepolia.json',
            'demoEvidence': '/runtime/demo_evidence.sepolia.json',
            'screenshotManifest': '/runtime/screenshot-manifest.sepolia.json',
        },
        'etherscanBaseUrl': SEPOLIA_ETHERSCAN_BASE_URL,
    }


def load_frontend_abi_bundle() -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    for name, path in FRONTEND_ABI_ARTIFACTS.items():
        artifact = load_json(path)
        if 'abi' not in artifact:
            raise ValueError(f'Artifact for {name} is missing the abi field: {path}')
        bundle[name] = {'abi': artifact['abi']}
    return bundle


def required_screenshot_paths(screenshot_manifest: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for entry in screenshot_manifest['screenshots']:
        if entry['required']:
            paths.append(ROOT / entry['expectedPath'])
    return paths


def load_gas_report() -> dict[str, Any]:
    return load_json(ANALYSIS_DIR / 'gas' / 'gas-report.json')


def load_slither_summary() -> dict[str, Any]:
    return load_json(ANALYSIS_DIR / 'static' / 'slither-summary.json')
