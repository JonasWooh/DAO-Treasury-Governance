from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3._utils.events import EventLogErrorFlags
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact, predict_create_address


ZERO_BYTES32 = b"\x00" * 32
WETH = 10**18


class InnovationTreasuryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "treasury": load_artifact("src/treasury/InnovationTreasury/InnovationTreasury.json"),
            "timelock": load_artifact(
                "lib/openzeppelin-contracts/contracts/governance/TimelockController/TimelockController.json"
            ),
            "mock_weth": load_artifact("src/mocks/MockWETH/MockWETH.json"),
            "mock_chainlink": load_artifact("src/mocks/MockChainlinkAggregatorV3/MockChainlinkAggregatorV3.json"),
            "mock_pool": load_artifact("src/mocks/MockAavePool/MockAavePool.json"),
            "mock_a_token": load_artifact("src/mocks/MockAToken/MockAToken.json"),
            "oracle": load_artifact("src/oracle/TreasuryOracle/TreasuryOracle.json"),
            "adapter": load_artifact("src/adapters/AaveWethAdapter/AaveWethAdapter.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.deployer = self.w3.eth.accounts[0]
        self.attacker = self.w3.eth.accounts[1]
        self.recipient = self.w3.eth.accounts[2]
        self.alt_recipient = self.w3.eth.accounts[3]
        self._salt_counter = 1

        self.timelock = self._deploy(
            "timelock",
            [1, [self.deployer], [self.deployer], self.deployer],
        )
        self.weth = self._deploy("mock_weth", [])
        self.pool = self._deploy("mock_pool", [self.weth.address])
        self.a_token = self.w3.eth.contract(
            address=self.pool.functions.aToken().call(),
            abi=self.artifacts["mock_a_token"]["abi"],
        )
        self.chainlink = self._deploy("mock_chainlink", [])
        self.oracle = self._deploy("oracle", [self.chainlink.address, 3_600])

        predicted_treasury = predict_create_address(self.deployer, self.w3.eth.get_transaction_count(self.deployer) + 1)
        self.adapter = self._deploy(
            "adapter",
            [predicted_treasury, self.weth.address, self.pool.address, self.a_token.address],
        )
        self.treasury = self._deploy(
            "treasury",
            [self.timelock.address, self.weth.address, self.oracle.address, self.adapter.address],
        )
        self.assertEqual(self.treasury.address, predicted_treasury)

        self._send(self.chainlink.functions.setRoundData(2_000 * 10**8, self._latest_timestamp(), 8))
        self._send(self.weth.functions.mint(self.treasury.address, 5 * WETH))

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.deployer})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _latest_timestamp(self) -> int:
        return self.eth_tester.get_block_by_number("latest")["timestamp"]

    def _next_salt(self) -> bytes:
        value = self._salt_counter.to_bytes(32, byteorder="big")
        self._salt_counter += 1
        return value

    def _execute_via_timelock(self, call, salt: bytes | None = None):
        op_salt = salt or self._next_salt()
        data = call._encode_transaction_data()

        self._send(self.timelock.functions.schedule(call.address, 0, data, ZERO_BYTES32, op_salt, 1))
        self.eth_tester.time_travel(self._latest_timestamp() + 2)
        self.eth_tester.mine_blocks(1)
        return self._send(self.timelock.functions.execute(call.address, 0, data, ZERO_BYTES32, op_salt))

    def _assert_reverts(self, fn):
        with self.assertRaises(TransactionFailed):
            fn()

    def _project(self, project_id: bytes):
        return self.treasury.functions.getProject(project_id).call()

    def test_direct_eoa_calls_revert_for_state_changing_treasury_functions(self):
        project_id = Web3.keccak(text="SMART_RECYCLING_KIOSK")

        self._assert_reverts(
            lambda: self.treasury.functions.approveProject(project_id, self.recipient, WETH, 2).transact(
                {"from": self.attacker}
            )
        )
        self._assert_reverts(
            lambda: self.treasury.functions.releaseMilestone(project_id, 0, WETH // 2).transact({"from": self.attacker})
        )
        self._assert_reverts(lambda: self.treasury.functions.depositIdleFunds(WETH).transact({"from": self.attacker}))
        self._assert_reverts(lambda: self.treasury.functions.withdrawIdleFunds(WETH).transact({"from": self.attacker}))
        self._assert_reverts(
            lambda: self.treasury.functions.setRiskPolicy(2_500, 1_500, 7_200).transact({"from": self.attacker})
        )

    def test_approve_project_records_state_and_emits_event(self):
        project_id = Web3.keccak(text="SMART_RECYCLING_KIOSK")
        receipt = self._execute_via_timelock(
            self.treasury.functions.approveProject(project_id, self.recipient, WETH, 2)
        )

        logs = self.treasury.events.ProjectApproved().process_receipt(receipt, errors=EventLogErrorFlags.Discard)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["args"]["projectId"], project_id)
        self.assertEqual(logs[0]["args"]["recipient"], self.recipient)
        self.assertEqual(logs[0]["args"]["maxBudgetWeth"], WETH)
        self.assertEqual(logs[0]["args"]["milestoneCount"], 2)

        project = self._project(project_id)
        self.assertEqual(project[0], self.recipient)
        self.assertEqual(project[1], WETH)
        self.assertEqual(project[2], 0)
        self.assertEqual(project[3], 2)
        self.assertEqual(project[4], 0)
        self.assertTrue(project[5])
        self.assertTrue(self.treasury.functions.projectIdUsed(project_id).call())

    def test_approve_project_reverts_for_invalid_inputs_and_budget_cap(self):
        project_id = Web3.keccak(text="OVER_CAP")

        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.approveProject(project_id, "0x0000000000000000000000000000000000000000", WETH, 2)
            )
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.approveProject(project_id, self.recipient, 0, 2)
            )
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.approveProject(project_id, self.recipient, WETH, 0)
            )
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.approveProject(project_id, self.recipient, int(1.1 * WETH), 2)
            )
        )

    def test_release_milestone_reverts_for_unapproved_and_inactive_projects(self):
        project_id = Web3.keccak(text="UNAPPROVED_OR_INACTIVE")

        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 0, WETH // 2)
            )
        )

        self._execute_via_timelock(self.treasury.functions.approveProject(project_id, self.recipient, WETH, 2))
        self._execute_via_timelock(self.treasury.functions.releaseMilestone(project_id, 0, WETH // 2))
        self._execute_via_timelock(self.treasury.functions.releaseMilestone(project_id, 1, WETH // 2))

        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 2, 1)
            )
        )
    def test_release_milestone_requires_strict_sequence_and_marks_completion(self):
        project_id = Web3.keccak(text="SEQUENTIAL_PROJECT")
        self._execute_via_timelock(self.treasury.functions.approveProject(project_id, self.recipient, WETH, 2))

        first_receipt = self._execute_via_timelock(
            self.treasury.functions.releaseMilestone(project_id, 0, WETH // 2)
        )
        first_logs = self.treasury.events.MilestoneReleased().process_receipt(
            first_receipt, errors=EventLogErrorFlags.Discard
        )
        self.assertEqual(first_logs[0]["args"]["milestoneIndex"], 0)
        self.assertEqual(first_logs[0]["args"]["amountWeth"], WETH // 2)
        self.assertFalse(first_logs[0]["args"]["projectCompleted"])

        project_after_first = self._project(project_id)
        self.assertEqual(project_after_first[2], WETH // 2)
        self.assertEqual(project_after_first[4], 1)
        self.assertTrue(project_after_first[5])

        second_receipt = self._execute_via_timelock(
            self.treasury.functions.releaseMilestone(project_id, 1, WETH // 2)
        )
        second_logs = self.treasury.events.MilestoneReleased().process_receipt(
            second_receipt, errors=EventLogErrorFlags.Discard
        )
        self.assertTrue(second_logs[0]["args"]["projectCompleted"])

        project_after_second = self._project(project_id)
        self.assertEqual(project_after_second[2], WETH)
        self.assertEqual(project_after_second[4], 2)
        self.assertFalse(project_after_second[5])

        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.approveProject(project_id, self.alt_recipient, WETH // 2, 1)
            )
        )

    def test_release_milestone_reverts_for_wrong_index_budget_and_liquidity(self):
        project_id = Web3.keccak(text="INVALID_RELEASE")
        self._execute_via_timelock(self.treasury.functions.approveProject(project_id, self.recipient, WETH, 2))

        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 1, WETH // 2)
            )
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 0, 0)
            )
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 0, WETH + 1)
            )
        )

        self._execute_via_timelock(self.treasury.functions.depositIdleFunds(3 * WETH))
        self._assert_reverts(
            lambda: self._execute_via_timelock(
                self.treasury.functions.releaseMilestone(project_id, 0, int(2.5 * WETH))
            )
        )

    def test_deposit_idle_funds_moves_weth_and_preserves_reserve_floor(self):
        receipt = self._execute_via_timelock(self.treasury.functions.depositIdleFunds(3 * WETH))

        logs = self.treasury.events.IdleFundsDeposited().process_receipt(receipt, errors=EventLogErrorFlags.Discard)
        self.assertEqual(logs[0]["args"]["amountWeth"], 3 * WETH)
        self.assertEqual(logs[0]["args"]["liquidBalanceAfterWeth"], 2 * WETH)
        self.assertEqual(logs[0]["args"]["suppliedBalanceAfterWeth"], 3 * WETH)

        self.assertEqual(self.treasury.functions.liquidWethBalance().call(), 2 * WETH)
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 3 * WETH)
        self.assertEqual(self.treasury.functions.totalManagedWeth().call(), 5 * WETH)
        self.assertEqual(self.weth.functions.balanceOf(self.pool.address).call(), 3 * WETH)
        self.assertEqual(self.a_token.functions.balanceOf(self.adapter.address).call(), 3 * WETH)
        self.assertEqual(self.weth.functions.allowance(self.treasury.address, self.adapter.address).call(), 0)
        self.assertEqual(self.weth.functions.allowance(self.adapter.address, self.pool.address).call(), 0)

    def test_deposit_idle_funds_reverts_on_zero_amount_overdraw_reserve_floor_and_protocol_mismatch(self):
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.depositIdleFunds(0)))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.depositIdleFunds(6 * WETH)))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.depositIdleFunds(4 * WETH)))

        self._send(self.pool.functions.setSupplyPullBps(5_000))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.depositIdleFunds(WETH)))

    def test_deposit_idle_funds_reverts_when_a_token_mint_is_not_exact(self):
        self._send(self.pool.functions.setSupplyMintBps(5_000))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.depositIdleFunds(WETH)))

    def test_withdraw_idle_funds_requires_exact_return(self):
        self._execute_via_timelock(self.treasury.functions.depositIdleFunds(3 * WETH))

        positive_receipt = self._execute_via_timelock(self.treasury.functions.withdrawIdleFunds(WETH))
        positive_logs = self.treasury.events.IdleFundsWithdrawn().process_receipt(
            positive_receipt, errors=EventLogErrorFlags.Discard
        )
        self.assertEqual(positive_logs[0]["args"]["amountWeth"], WETH)
        self.assertEqual(self.treasury.functions.liquidWethBalance().call(), 3 * WETH)
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 2 * WETH)

        self._send(self.pool.functions.setWithdrawReturnBps(5_000))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.withdrawIdleFunds(WETH)))

    def test_withdraw_idle_funds_reverts_when_treasury_credit_is_not_exact(self):
        self._execute_via_timelock(self.treasury.functions.depositIdleFunds(3 * WETH))
        self._send(self.pool.functions.setWithdrawTransferBps(5_000))
        self._assert_reverts(lambda: self._execute_via_timelock(self.treasury.functions.withdrawIdleFunds(WETH)))

    def test_set_risk_policy_updates_values_and_reverts_on_invalid_inputs(self):
        receipt = self._execute_via_timelock(self.treasury.functions.setRiskPolicy(2_500, 1_500, 7_200))
        logs = self.treasury.events.RiskPolicyUpdated().process_receipt(receipt, errors=EventLogErrorFlags.Discard)
        self.assertEqual(logs[0]["args"]["minLiquidReserveBps"], 2_500)
        self.assertEqual(logs[0]["args"]["maxSingleGrantBps"], 1_500)
        self.assertEqual(logs[0]["args"]["stalePriceThreshold"], 7_200)
        self.assertEqual(self.treasury.functions.riskPolicy().call(), [2_500, 1_500, 7_200])

        self._assert_reverts(
            lambda: self._execute_via_timelock(self.treasury.functions.setRiskPolicy(10_001, 1_500, 7_200))
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(self.treasury.functions.setRiskPolicy(2_500, 10_001, 7_200))
        )
        self._assert_reverts(
            lambda: self._execute_via_timelock(self.treasury.functions.setRiskPolicy(2_500, 1_500, 0))
        )

    def test_nav_usd_uses_real_oracle_and_live_supplied_balance(self):
        self._execute_via_timelock(self.treasury.functions.depositIdleFunds(3 * WETH))
        self.assertEqual(self.treasury.functions.navUsd().call(), 10_000 * WETH)

        self._send(self.pool.functions.accrueYield(self.adapter.address, WETH // 2))
        self.assertEqual(self.treasury.functions.suppliedWethBalance().call(), 7 * WETH // 2)
        self.assertEqual(self.treasury.functions.totalManagedWeth().call(), 11 * WETH // 2)
        self.assertEqual(self.treasury.functions.navUsd().call(), 11_000 * WETH)

        self._send(self.chainlink.functions.setRoundData(0, self._latest_timestamp(), 8))
        self._assert_reverts(lambda: self.treasury.functions.navUsd().call())

        self._send(self.chainlink.functions.setRoundData(2_000 * 10**8, 0, 8))
        self._assert_reverts(lambda: self.treasury.functions.navUsd().call())

        stale_timestamp = self._latest_timestamp() - 3_700
        self._send(self.chainlink.functions.setRoundData(2_000 * 10**8, stale_timestamp, 8))
        self._assert_reverts(lambda: self.treasury.functions.navUsd().call())


if __name__ == "__main__":
    unittest.main()