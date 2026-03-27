from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact


WETH = 10**18


class AaveWethAdapterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "adapter": load_artifact("src/adapters/AaveWethAdapter/AaveWethAdapter.json"),
            "mock_weth": load_artifact("src/mocks/MockWETH/MockWETH.json"),
            "mock_pool": load_artifact("src/mocks/MockAavePool/MockAavePool.json"),
            "mock_a_token": load_artifact("src/mocks/MockAToken/MockAToken.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.treasury = self.w3.eth.accounts[0]
        self.attacker = self.w3.eth.accounts[1]

        self.weth = self._deploy("mock_weth", [])
        self.pool = self._deploy("mock_pool", [self.weth.address])
        self.a_token = self.w3.eth.contract(
            address=self.pool.functions.aToken().call(),
            abi=self.artifacts["mock_a_token"]["abi"],
        )
        self.adapter = self._deploy(
            "adapter",
            [self.treasury, self.weth.address, self.pool.address, self.a_token.address],
        )

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.treasury})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.treasury})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _assert_reverts(self, fn):
        with self.assertRaises(TransactionFailed):
            fn()

    def _mint_and_approve(self, amount_weth: int) -> None:
        self._send(self.weth.functions.mint(self.treasury, amount_weth))
        self._send(self.weth.functions.approve(self.adapter.address, amount_weth))

    def _prime_supply(self, amount_weth: int) -> None:
        self._mint_and_approve(amount_weth)
        self._send(self.adapter.functions.supply(amount_weth))

    def test_constructor_rejects_zero_addresses(self):
        contract = self.w3.eth.contract(
            abi=self.artifacts["adapter"]["abi"],
            bytecode=self.artifacts["adapter"]["bytecode"],
        )

        self._assert_reverts(
            lambda: contract.constructor(
                "0x0000000000000000000000000000000000000000",
                self.weth.address,
                self.pool.address,
                self.a_token.address,
            ).transact({"from": self.treasury})
        )
        self._assert_reverts(
            lambda: contract.constructor(
                self.treasury,
                "0x0000000000000000000000000000000000000000",
                self.pool.address,
                self.a_token.address,
            ).transact({"from": self.treasury})
        )

    def test_only_treasury_can_call_supply_and_withdraw(self):
        self._mint_and_approve(WETH)
        self._assert_reverts(lambda: self.adapter.functions.supply(WETH).transact({"from": self.attacker}))
        self._prime_supply(WETH)
        self._assert_reverts(lambda: self.adapter.functions.withdraw(WETH).transact({"from": self.attacker}))

    def test_supply_moves_weth_clears_allowance_and_tracks_supplied_balance(self):
        self._mint_and_approve(3 * WETH)
        self._send(self.adapter.functions.supply(3 * WETH))

        self.assertEqual(self.weth.functions.balanceOf(self.treasury).call(), 0)
        self.assertEqual(self.weth.functions.balanceOf(self.pool.address).call(), 3 * WETH)
        self.assertEqual(self.a_token.functions.balanceOf(self.adapter.address).call(), 3 * WETH)
        self.assertEqual(self.adapter.functions.suppliedBalance().call(), 3 * WETH)
        self.assertEqual(self.weth.functions.allowance(self.adapter.address, self.pool.address).call(), 0)

    def test_supply_reverts_on_zero_amount_and_pool_pull_mismatch(self):
        self._assert_reverts(lambda: self.adapter.functions.supply(0).transact({"from": self.treasury}))

        self._mint_and_approve(WETH)
        self._send(self.pool.functions.setSupplyPullBps(5_000))
        self._assert_reverts(lambda: self.adapter.functions.supply(WETH).transact({"from": self.treasury}))

    def test_supply_reverts_when_a_token_mint_is_not_exact(self):
        self._mint_and_approve(WETH)
        self._send(self.pool.functions.setSupplyMintBps(5_000))
        self._assert_reverts(lambda: self.adapter.functions.supply(WETH).transact({"from": self.treasury}))

    def test_withdraw_requires_exact_return_and_exact_treasury_credit(self):
        self._prime_supply(3 * WETH)
        self._send(self.adapter.functions.withdraw(WETH))
        self.assertEqual(self.weth.functions.balanceOf(self.treasury).call(), WETH)
        self.assertEqual(self.adapter.functions.suppliedBalance().call(), 2 * WETH)

        self._send(self.pool.functions.setWithdrawReturnBps(5_000))
        self._assert_reverts(lambda: self.adapter.functions.withdraw(WETH).transact({"from": self.treasury}))

    def test_withdraw_reverts_when_treasury_credit_is_not_exact(self):
        self._prime_supply(2 * WETH)
        self._send(self.pool.functions.setWithdrawTransferBps(5_000))
        self._assert_reverts(lambda: self.adapter.functions.withdraw(WETH).transact({"from": self.treasury}))

    def test_supplied_balance_reflects_live_a_token_balance(self):
        self._prime_supply(2 * WETH)
        self._send(self.pool.functions.accrueYield(self.adapter.address, WETH // 10))

        self.assertEqual(self.adapter.functions.suppliedBalance().call(), 21 * WETH // 10)


if __name__ == "__main__":
    unittest.main()