from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
TEMP_ROOT = ROOT / 'test' / '.tmp'
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def make_test_dir() -> Path:
    path = TEMP_ROOT / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path


def make_manifests(base_dir: Path) -> dict[str, Path]:
    deployment_path = base_dir / 'deployments.sepolia.json'
    scenario_path = base_dir / 'proposal_scenarios.sepolia.json'
    evidence_path = base_dir / 'demo_evidence.sepolia.json'
    screenshot_path = base_dir / 'screenshot-manifest.sepolia.json'

    deployment_manifest = {
        'network': {'name': 'sepolia', 'chainId': 11155111},
        'contracts': {
            'CampusInnovationFundToken': '0x1000000000000000000000000000000000000001',
            'InnovationGovernor': '0x1000000000000000000000000000000000000002',
            'TimelockController': '0x1000000000000000000000000000000000000003',
            'InnovationTreasury': '0x1000000000000000000000000000000000000004',
            'TreasuryOracle': '0x1000000000000000000000000000000000000005',
            'AaveWethAdapter': '0x1000000000000000000000000000000000000006',
        },
        'externalProtocols': {
            'WETH': '0x1000000000000000000000000000000000000007',
            'ChainlinkEthUsdFeed': '0x1000000000000000000000000000000000000008',
            'AavePool': '0x1000000000000000000000000000000000000009',
            'AaveAWeth': '0x1000000000000000000000000000000000000010',
        },
        'transactions': {
            'deployToken': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        },
    }
    scenario_manifest = {
        'project': {
            'name': 'Smart Recycling Kiosk',
            'projectKey': 'SMART_RECYCLING_KIOSK',
            'projectId': '0x1111111111111111111111111111111111111111111111111111111111111111',
            'recipient': '0x2000000000000000000000000000000000000004',
            'maxBudgetWeth': '1000000000000000000',
            'milestoneCount': 2,
        },
        'proposals': [
            {
                'slug': 'proposal1_approve_project',
                'title': 'Proposal 1',
                'description': 'Proposal 1: Approve Smart Recycling Kiosk project',
                'targets': ['0x1000000000000000000000000000000000000004'],
                'values': ['0'],
                'calldatas': ['0xaaaa'],
                'descriptionHash': '0x2222222222222222222222222222222222222222222222222222222222222222',
                'proposalId': '101',
                'operationId': '0x3333333333333333333333333333333333333333333333333333333333333333',
                'expectedOutcome': {'projectActive': True},
            }
        ],
    }
    evidence_manifest = {
        'network': {'name': 'sepolia', 'chainId': 11155111},
        'contracts': deployment_manifest['contracts'],
        'participants': {
            'voterA': '0x2000000000000000000000000000000000000001',
            'voterB': '0x2000000000000000000000000000000000000002',
            'voterC': '0x2000000000000000000000000000000000000003',
        },
        'project': {
            'projectId': scenario_manifest['project']['projectId'],
            'recipient': scenario_manifest['project']['recipient'],
        },
        'seedState': {
            'fundTreasury': {
                'transactionHash': '0x6666666666666666666666666666666666666666666666666666666666666666',
            },
            'selfDelegations': {
                'voterA': {'transactionHash': '0x7777777777777777777777777777777777777777777777777777777777777777'},
            },
        },
        'proposals': {
            'proposal1_approve_project': {
                'proposalId': '101',
                'transactions': {
                    'propose': '0x8888888888888888888888888888888888888888888888888888888888888888',
                    'votes': {'voterA': '0x9999999999999999999999999999999999999999999999999999999999999999'},
                    'queue': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',
                    'execute': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2',
                },
            },
            'proposal2_deposit_idle_funds': {
                'proposalId': '102',
                'transactions': {
                    'propose': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1',
                    'queue': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb2',
                    'execute': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb3',
                },
                'snapshots': {
                    'postExecution': {
                        'treasury': {
                            'liquidWeth': '2000000000000000000',
                            'suppliedWeth': '3000000000000000000',
                            'totalManagedWeth': '5000000000000000000',
                            'navUsd': '10000000000000000000000',
                        }
                    }
                },
            },
        },
        'etherscanLinks': {
            'addresses': {},
            'transactions': {},
        },
    }
    screenshot_manifest = {
        'network': {'name': 'sepolia', 'chainId': 11155111},
        'generatedAt': '2026-03-27T00:00:00Z',
        'screenshots': [
            {
                'id': 'required-shot',
                'caption': 'Required screenshot',
                'reportSection': 'Sepolia deployment and evidence',
                'expectedPath': str(base_dir / 'required-shot.png'),
                'required': True,
                'category': 'evidence',
            }
        ],
    }

    write_json(deployment_path, deployment_manifest)
    write_json(scenario_path, scenario_manifest)
    write_json(evidence_path, evidence_manifest)
    write_json(screenshot_path, screenshot_manifest)

    return {
        'deployment': deployment_path,
        'scenario': scenario_path,
        'evidence': evidence_path,
        'screenshot': screenshot_path,
    }


class SubmissionDeliverablesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._created_dirs: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self._created_dirs):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

    def create_workspace(self) -> Path:
        path = make_test_dir()
        self._created_dirs.append(path)
        return path

    def test_export_frontend_bundle_writes_expected_files(self) -> None:
        base = self.create_workspace()
        manifests = make_manifests(base)
        frontend_config = base / 'frontend.config.sepolia.json'
        frontend_runtime_dir = base / 'runtime'
        frontend_abi_dir = base / 'abi'

        completed = subprocess.run(
            [
                PYTHON,
                str(ROOT / 'scripts' / 'export_frontend_bundle.py'),
                '--deployment-manifest', str(manifests['deployment']),
                '--scenario-manifest', str(manifests['scenario']),
                '--evidence-manifest', str(manifests['evidence']),
                '--screenshot-manifest', str(manifests['screenshot']),
                '--frontend-config-output', str(frontend_config),
                '--frontend-runtime-dir', str(frontend_runtime_dir),
                '--frontend-abi-dir', str(frontend_abi_dir),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(frontend_config.exists())
        self.assertTrue((frontend_runtime_dir / 'deployments.sepolia.json').exists())
        self.assertTrue((frontend_abi_dir / 'InnovationTreasury.json').exists())

    def test_generate_treasury_workbook_creates_required_sheets(self) -> None:
        base = self.create_workspace()
        manifests = make_manifests(base)
        workbook_path = base / 'treasury_analysis.xlsx'
        summary_path = base / 'treasury_analysis.summary.json'

        completed = subprocess.run(
            [
                PYTHON,
                str(ROOT / 'scripts' / 'generate_treasury_workbook.py'),
                '--evidence-manifest', str(manifests['evidence']),
                '--output', str(workbook_path),
                '--summary-output', str(summary_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(workbook_path.exists())
        self.assertTrue(summary_path.exists())
        with zipfile.ZipFile(workbook_path) as archive:
            workbook_xml = archive.read('xl/workbook.xml').decode('utf-8')
        self.assertIn('Inputs', workbook_xml)
        self.assertIn('ScenarioMatrix', workbook_xml)
        self.assertIn('NAVProjection', workbook_xml)
        self.assertIn('ReserveSensitivity', workbook_xml)
        self.assertIn('Charts', workbook_xml)
        self.assertIn('Commentary', workbook_xml)

    def test_generate_final_report_refuses_missing_screenshots(self) -> None:
        base = self.create_workspace()
        manifests = make_manifests(base)
        summary_path = base / 'treasury_analysis.summary.json'
        summary_path.write_text(json.dumps({'startingState': {'totalManagedWeth': 5.0, 'liquidWeth': 2.0, 'suppliedWeth': 3.0, 'ethPriceUsd': 2000.0}, 'scenarioCount': 27, 'worstCase': {'scenario': 'Bear / 0% / Heavy', 'navUsd': 7000.0}, 'bestCase': {'scenario': 'Bull / 6% APR / Light', 'navUsd': 14000.0}}, indent=2), encoding='utf-8')
        output_path = base / 'final_report.pdf'

        completed = subprocess.run(
            [
                PYTHON,
                str(ROOT / 'scripts' / 'generate_final_report.py'),
                '--deployment-manifest', str(manifests['deployment']),
                '--scenario-manifest', str(manifests['scenario']),
                '--evidence-manifest', str(manifests['evidence']),
                '--screenshot-manifest', str(manifests['screenshot']),
                '--workbook-summary', str(summary_path),
                '--output', str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('Required screenshots are missing', completed.stderr + completed.stdout)

    def test_validate_submission_package_catches_missing_report(self) -> None:
        base = self.create_workspace()
        manifests = make_manifests(base)
        workbook_path = base / 'treasury_analysis.xlsx'
        workbook_path.write_text('placeholder', encoding='utf-8')
        frontend_config = base / 'frontend.config.sepolia.json'
        frontend_config.write_text(json.dumps({
            'configured': True,
            'network': {'name': 'sepolia', 'chainId': 11155111},
            'contracts': {
                'CampusInnovationFundToken': '0x1000000000000000000000000000000000000001',
                'InnovationGovernor': '0x1000000000000000000000000000000000000002',
                'TimelockController': '0x1000000000000000000000000000000000000003',
                'InnovationTreasury': '0x1000000000000000000000000000000000000004',
                'TreasuryOracle': '0x1000000000000000000000000000000000000005',
                'AaveWethAdapter': '0x1000000000000000000000000000000000000006'
            }
        }, indent=2), encoding='utf-8')

        completed = subprocess.run(
            [
                PYTHON,
                str(ROOT / 'scripts' / 'validate_submission_package.py'),
                '--deployment-manifest', str(manifests['deployment']),
                '--scenario-manifest', str(manifests['scenario']),
                '--evidence-manifest', str(manifests['evidence']),
                '--screenshot-manifest', str(manifests['screenshot']),
                '--frontend-config', str(frontend_config),
                '--workbook', str(workbook_path),
                '--report', str(base / 'missing_report.pdf'),
                '--skip-frontend-build',
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn('Missing report PDF', completed.stderr + completed.stdout)


if __name__ == '__main__':
    unittest.main()
