from __future__ import annotations

import argparse
from pathlib import Path

from deliverable_common import (
    DEPLOYMENT_MANIFEST_PATH,
    EVIDENCE_MANIFEST_PATH,
    FUNDING_STATE_PATH,
    FRONTEND_ABI_DIR,
    FRONTEND_CONFIG_PATH,
    FRONTEND_RUNTIME_DIR,
    SCENARIO_MANIFEST_PATH,
    SCREENSHOT_MANIFEST_PATH,
    export_frontend_config_payload,
    load_frontend_abi_bundle,
    load_required_manifests,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Export the frontend ABI/config/runtime bundle from authoritative Sepolia manifests.')
    parser.add_argument('--deployment-manifest', default=str(DEPLOYMENT_MANIFEST_PATH))
    parser.add_argument('--scenario-manifest', default=str(SCENARIO_MANIFEST_PATH))
    parser.add_argument('--evidence-manifest', default=str(EVIDENCE_MANIFEST_PATH))
    parser.add_argument('--funding-state-manifest', default=str(FUNDING_STATE_PATH))
    parser.add_argument('--screenshot-manifest', default=str(SCREENSHOT_MANIFEST_PATH))
    parser.add_argument('--frontend-config-output', default=str(FRONTEND_CONFIG_PATH))
    parser.add_argument('--frontend-runtime-dir', default=str(FRONTEND_RUNTIME_DIR))
    parser.add_argument('--frontend-abi-dir', default=str(FRONTEND_ABI_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifests = load_required_manifests(
        Path(args.deployment_manifest),
        Path(args.scenario_manifest),
        Path(args.evidence_manifest),
        Path(args.funding_state_manifest),
        Path(args.screenshot_manifest),
    )

    frontend_config_output = Path(args.frontend_config_output)
    frontend_runtime_dir = Path(args.frontend_runtime_dir)
    frontend_abi_dir = Path(args.frontend_abi_dir)

    frontend_runtime_dir.mkdir(parents=True, exist_ok=True)
    frontend_abi_dir.mkdir(parents=True, exist_ok=True)

    write_json(frontend_config_output, export_frontend_config_payload(manifests['deployment']))

    abi_bundle = load_frontend_abi_bundle()
    for name, payload in abi_bundle.items():
        write_json(frontend_abi_dir / f'{name}.json', payload)

    write_json(frontend_runtime_dir / 'deployments.sepolia.json', manifests['deployment'])
    write_json(frontend_runtime_dir / 'proposal_scenarios.sepolia.json', manifests['scenario'])
    write_json(frontend_runtime_dir / 'demo_evidence.sepolia.json', manifests['evidence'])
    write_json(frontend_runtime_dir / 'funding_state.sepolia.json', manifests['funding_state'])
    write_json(frontend_runtime_dir / 'screenshot-manifest.sepolia.json', manifests['screenshot'])

    print(f'Frontend config written to {frontend_config_output}')
    print(f'Frontend runtime manifests written to {frontend_runtime_dir}')
    print(f'Frontend ABI bundle written to {frontend_abi_dir}')


if __name__ == '__main__':
    main()
