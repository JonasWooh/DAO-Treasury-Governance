from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eth_tester import EthereumTester, PyEVMBackend
from solcx import compile_standard
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

import compile_contracts
from test.support import predict_create_address


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "analysis" / "gas"
GAS_JSON = ANALYSIS_DIR / "gas-report.json"
GAS_MD = ANALYSIS_DIR / "gas-report.md"

TOKEN_UNIT = 10**18
INITIAL_ALLOCATION = 200_000 * TOKEN_UNIT
TIMELOCK_DELAY_SECONDS = 120
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
SUPPORT_FOR = 1


def compile_variant(overrides: dict[str, str]) -> dict:
    compile_contracts.ensure_solc_available(install_requested=False)
    sources = compile_contracts.collect_entry_sources()
    for source_name, source_content in overrides.items():
        sources[source_name] = {"content": source_content}

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": sources,
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "metadata": {"bytecodeHash": "none"},
                "remappings": compile_contracts.REMAPPINGS,
                "outputSelection": {
                    "*": {
                        "*": [
                            "abi",
                            "evm.bytecode.object",
                        ]
                    }
                },
            },
        },
        base_path=str(ROOT),
        allow_paths=str(ROOT),
    )

    errors = [entry for entry in compiled.get("errors", []) if entry.get("severity") == "error"]
    if errors:
        raise RuntimeError(json.dumps(errors, indent=2))

    return compiled


def artifact(compiled: dict, source_name: str, contract_name: str) -> dict:
    contract_output = compiled["contracts"][source_name][contract_name]
    return {
        "abi": contract_output["abi"],
        "bytecode": contract_output["evm"]["bytecode"]["object"],
    }


def deploy_contract(w3: Web3, artifact_payload: dict, constructor_args: list, sender: str):
    contract = w3.eth.contract(abi=artifact_payload["abi"], bytecode=artifact_payload["bytecode"])
    tx_hash = contract.constructor(*constructor_args).transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=receipt.contractAddress, abi=artifact_payload["abi"]), receipt


def send(call, sender: str, w3: Web3):
    tx_hash = call.transact({"from": sender})
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def build_baseline_treasury_source() -> str:
    source_path = ROOT / "src" / "treasury" / "InnovationTreasury.sol"
    source = source_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    source = source.replace(
        "        uint256 suppliedBefore = suppliedWethBalance();\n        uint256 totalManagedBefore = liquidBefore + suppliedBefore;",
        "        uint256 totalManagedBefore = liquidBefore + suppliedWethBalance();",
    )
    source = source.replace(
        "        uint256 suppliedAfter = totalManagedBefore - liquidAfterObserved;\n\n        emit IdleFundsDeposited(amountWeth, liquidAfterObserved, suppliedAfter);",
        "        emit IdleFundsDeposited(amountWeth, liquidAfterObserved, suppliedWethBalance());",
    )
    source = source.replace(
        "        uint256 liquidBefore = liquidWethBalance();\n        uint256 suppliedBefore = suppliedWethBalance();\n        aaveWethAdapter.withdraw(amountWeth);",
        "        uint256 liquidBefore = liquidWethBalance();\n        aaveWethAdapter.withdraw(amountWeth);",
    )
    source = source.replace(
        "        uint256 suppliedAfter = suppliedBefore - amountWeth;\n\n        emit IdleFundsWithdrawn(amountWeth, liquidAfter, suppliedAfter);",
        "        emit IdleFundsWithdrawn(amountWeth, liquidAfter, suppliedWethBalance());",
    )
    return source


def measure_governance_actions(compiled: dict) -> dict[str, int]:
    eth_tester = EthereumTester(PyEVMBackend())
    w3 = Web3(EthereumTesterProvider(eth_tester))
    deployer = w3.eth.accounts[0]
    voter_a = w3.eth.accounts[1]
    voter_b = w3.eth.accounts[2]

    timelock, _ = deploy_contract(
        w3,
        artifact(compiled, "lib/openzeppelin-contracts/contracts/governance/TimelockController.sol", "TimelockController"),
        [TIMELOCK_DELAY_SECONDS, [], [ZERO_ADDRESS], deployer],
        deployer,
    )
    token, _ = deploy_contract(
        w3,
        artifact(compiled, "src/governance/CampusInnovationFundToken.sol", "CampusInnovationFundToken"),
        [deployer],
        deployer,
    )
    governor, _ = deploy_contract(
        w3,
        artifact(compiled, "src/governance/InnovationGovernor.sol", "InnovationGovernor"),
        [token.address, timelock.address],
        deployer,
    )
    target, _ = deploy_contract(
        w3,
        artifact(compiled, "src/mocks/GovernedActionTarget.sol", "GovernedActionTarget"),
        [timelock.address],
        deployer,
    )

    send(token.functions.mint(voter_a, INITIAL_ALLOCATION), deployer, w3)
    send(token.functions.mint(voter_b, INITIAL_ALLOCATION), deployer, w3)
    send(token.functions.delegate(voter_a), voter_a, w3)
    send(token.functions.delegate(voter_b), voter_b, w3)

    proposer_role = timelock.functions.PROPOSER_ROLE().call()
    canceller_role = timelock.functions.CANCELLER_ROLE().call()
    admin_role = timelock.functions.DEFAULT_ADMIN_ROLE().call()
    send(timelock.functions.grantRole(proposer_role, governor.address), deployer, w3)
    send(timelock.functions.grantRole(canceller_role, governor.address), deployer, w3)
    send(timelock.functions.renounceRole(admin_role, deployer), deployer, w3)

    targets = [target.address]
    values = [0]
    calldatas = [target.functions.setTrackedValue(77)._encode_transaction_data()]
    description = "Gas report proposal"
    description_hash = Web3.keccak(text=description)

    propose_receipt = send(governor.functions.propose(targets, values, calldatas, description), voter_a, w3)
    proposal_id = governor.functions.hashProposal(targets, values, calldatas, description_hash).call()

    eth_tester.mine_blocks(1)
    cast_vote_receipt = send(governor.functions.castVote(proposal_id, SUPPORT_FOR), voter_a, w3)
    send(governor.functions.castVote(proposal_id, SUPPORT_FOR), voter_b, w3)
    eth_tester.mine_blocks(21)

    queue_receipt = send(governor.functions.queue(targets, values, calldatas, description_hash), voter_a, w3)

    eth_tester.time_travel(eth_tester.get_block_by_number("latest")["timestamp"] + TIMELOCK_DELAY_SECONDS + 1)
    eth_tester.mine_blocks(1)
    execute_receipt = send(governor.functions.execute(targets, values, calldatas, description_hash), voter_b, w3)

    return {
        "propose": propose_receipt.gasUsed,
        "castVote": cast_vote_receipt.gasUsed,
        "queue": queue_receipt.gasUsed,
        "execute": execute_receipt.gasUsed,
    }


def setup_treasury_harness(compiled: dict):
    eth_tester = EthereumTester(PyEVMBackend())
    w3 = Web3(EthereumTesterProvider(eth_tester))
    deployer = w3.eth.accounts[0]
    recipient = w3.eth.accounts[1]

    weth, _ = deploy_contract(
        w3,
        artifact(compiled, "src/mocks/MockWETH.sol", "MockWETH"),
        [],
        deployer,
    )
    pool, _ = deploy_contract(
        w3,
        artifact(compiled, "src/mocks/MockAavePool.sol", "MockAavePool"),
        [weth.address],
        deployer,
    )
    a_token = w3.eth.contract(
        address=pool.functions.aToken().call(),
        abi=artifact(compiled, "src/mocks/MockAToken.sol", "MockAToken")["abi"],
    )
    chainlink, _ = deploy_contract(
        w3,
        artifact(compiled, "src/mocks/MockChainlinkAggregatorV3.sol", "MockChainlinkAggregatorV3"),
        [],
        deployer,
    )
    oracle, _ = deploy_contract(
        w3,
        artifact(compiled, "src/oracle/TreasuryOracle.sol", "TreasuryOracle"),
        [chainlink.address, 3_600],
        deployer,
    )

    predicted_treasury = predict_create_address(deployer, w3.eth.get_transaction_count(deployer) + 1)
    adapter, _ = deploy_contract(
        w3,
        artifact(compiled, "src/adapters/AaveWethAdapter.sol", "AaveWethAdapter"),
        [predicted_treasury, weth.address, pool.address, a_token.address],
        deployer,
    )
    treasury, _ = deploy_contract(
        w3,
        artifact(compiled, "src/treasury/InnovationTreasury.sol", "InnovationTreasury"),
        [deployer, weth.address, oracle.address, adapter.address],
        deployer,
    )

    send(chainlink.functions.setRoundData(2_000 * 10**8, eth_tester.get_block_by_number("latest")["timestamp"], 8), deployer, w3)
    send(weth.functions.mint(treasury.address, 5 * TOKEN_UNIT), deployer, w3)

    return {
        "eth_tester": eth_tester,
        "w3": w3,
        "deployer": deployer,
        "recipient": recipient,
        "treasury": treasury,
    }


def measure_treasury_actions(compiled: dict) -> dict[str, int]:
    project_id = Web3.keccak(text="GAS_PROJECT")

    approve_harness = setup_treasury_harness(compiled)
    approve_receipt = send(
        approve_harness["treasury"].functions.approveProject(project_id, approve_harness["recipient"], TOKEN_UNIT, 2),
        approve_harness["deployer"],
        approve_harness["w3"],
    )

    release_harness = setup_treasury_harness(compiled)
    send(
        release_harness["treasury"].functions.approveProject(project_id, release_harness["recipient"], TOKEN_UNIT, 2),
        release_harness["deployer"],
        release_harness["w3"],
    )
    release_receipt = send(
        release_harness["treasury"].functions.releaseMilestone(project_id, 0, TOKEN_UNIT // 2),
        release_harness["deployer"],
        release_harness["w3"],
    )

    deposit_harness = setup_treasury_harness(compiled)
    deposit_receipt = send(
        deposit_harness["treasury"].functions.depositIdleFunds(3 * TOKEN_UNIT),
        deposit_harness["deployer"],
        deposit_harness["w3"],
    )

    withdraw_harness = setup_treasury_harness(compiled)
    send(
        withdraw_harness["treasury"].functions.depositIdleFunds(3 * TOKEN_UNIT),
        withdraw_harness["deployer"],
        withdraw_harness["w3"],
    )
    withdraw_receipt = send(
        withdraw_harness["treasury"].functions.withdrawIdleFunds(TOKEN_UNIT),
        withdraw_harness["deployer"],
        withdraw_harness["w3"],
    )

    return {
        "approveProject": approve_receipt.gasUsed,
        "releaseMilestone": release_receipt.gasUsed,
        "depositIdleFunds": deposit_receipt.gasUsed,
        "withdrawIdleFunds": withdraw_receipt.gasUsed,
    }


def build_report(governance_gas: dict[str, int], baseline_treasury_gas: dict[str, int], optimized_treasury_gas: dict[str, int]) -> dict:
    baseline = {**governance_gas, **baseline_treasury_gas}
    optimized = {**governance_gas, **optimized_treasury_gas}
    delta = {
        action: optimized[action] - baseline[action]
        for action in optimized
    }
    percent_delta = {
        action: round((delta[action] / baseline[action]) * 100, 2) if baseline[action] else 0.0
        for action in optimized
    }
    return {
        "optimization": {
            "title": "Reuse already-known Treasury supplied balances in deposit/withdraw events",
            "before": "InnovationTreasury emitted post-action supplied balances by calling suppliedWethBalance() again.",
            "after": "InnovationTreasury now reuses already-known balance deltas to compute supplied balances without an extra adapter read.",
        },
        "baseline": baseline,
        "optimized": optimized,
        "delta": delta,
        "percentDelta": percent_delta,
    }


def write_report(report: dict) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    GAS_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows = []
    for action in [
        "propose",
        "castVote",
        "queue",
        "execute",
        "approveProject",
        "releaseMilestone",
        "depositIdleFunds",
        "withdrawIdleFunds",
    ]:
        rows.append(
            f"| {action} | {report['baseline'][action]} | {report['optimized'][action]} | {report['delta'][action]} | {report['percentDelta'][action]}% |"
        )

    markdown = "\n".join(
        [
            "# Gas Report",
            "",
            "## Optimization Pass",
            "",
            f"- Baseline: {report['optimization']['before']}",
            f"- Optimized: {report['optimization']['after']}",
            "",
            "## Measured Actions",
            "",
            "| Action | Baseline Gas | Optimized Gas | Delta | Delta % |",
            "|---|---:|---:|---:|---:|",
            *rows,
            "",
            "## Notes",
            "",
            "- Governance actions are unchanged by this optimization pass, so their baseline and optimized measurements are identical.",
            "- Treasury action gas was measured against a direct-owner local harness to isolate contract-level execution cost.",
            "- Baseline Treasury measurements were compiled from the pre-optimization event-accounting variant of InnovationTreasury.",
        ]
    )
    GAS_MD.write_text(markdown, encoding="utf-8")


def main() -> None:
    current_compiled = compile_variant({})
    baseline_compiled = compile_variant({"src/treasury/InnovationTreasury.sol": build_baseline_treasury_source()})

    governance_gas = measure_governance_actions(current_compiled)
    baseline_treasury_gas = measure_treasury_actions(baseline_compiled)
    optimized_treasury_gas = measure_treasury_actions(current_compiled)

    report = build_report(governance_gas, baseline_treasury_gas, optimized_treasury_gas)
    write_report(report)
    print(f"Gas report written to {GAS_JSON} and {GAS_MD}")


if __name__ == "__main__":
    main()