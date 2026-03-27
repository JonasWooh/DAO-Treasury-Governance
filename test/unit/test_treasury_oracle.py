from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact


WETH = 10**18


class TreasuryOracleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "oracle": load_artifact("src/oracle/TreasuryOracle/TreasuryOracle.json"),
            "aggregator": load_artifact("src/mocks/MockChainlinkAggregatorV3/MockChainlinkAggregatorV3.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.deployer = self.w3.eth.accounts[0]

        self.aggregator = self._deploy("aggregator", [])
        self.oracle = self._deploy("oracle", [self.aggregator.address, 3_600])

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call):
        tx_hash = call.transact({"from": self.deployer})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _latest_timestamp(self) -> int:
        return self.eth_tester.get_block_by_number("latest")["timestamp"]

    def _assert_reverts(self, fn):
        with self.assertRaises(TransactionFailed):
            fn()

    def test_constructor_rejects_zero_feed_and_zero_threshold(self):
        contract = self.w3.eth.contract(
            abi=self.artifacts["oracle"]["abi"],
            bytecode=self.artifacts["oracle"]["bytecode"],
        )

        self._assert_reverts(
            lambda: contract.constructor("0x0000000000000000000000000000000000000000", 3_600).transact(
                {"from": self.deployer}
            )
        )
        self._assert_reverts(lambda: contract.constructor(self.aggregator.address, 0).transact({"from": self.deployer}))

    def test_latest_eth_usd_returns_feed_data_and_is_stale_tracks_threshold(self):
        now = self._latest_timestamp()
        self._send(self.aggregator.functions.setRoundData(2_000 * 10**8, now, 8))

        self.assertEqual(list(self.oracle.functions.latestEthUsd().call()), [2_000 * 10**8, now, 8])
        self.assertFalse(self.oracle.functions.isStale().call())

        self.eth_tester.time_travel(now + 3_601)
        self.eth_tester.mine_blocks(1)
        self.assertTrue(self.oracle.functions.isStale().call())

    def test_nav_usd_normalizes_decimals_below_equal_and_above_18(self):
        now = self._latest_timestamp()

        self._send(self.aggregator.functions.setRoundData(2_000 * 10**8, now, 8))
        self.assertEqual(self.oracle.functions.navUsd(5 * WETH).call(), 10_000 * WETH)

        self._send(self.aggregator.functions.setRoundData(2_000 * WETH, now, 18))
        self.assertEqual(self.oracle.functions.navUsd(WETH).call(), 2_000 * WETH)

        self._send(self.aggregator.functions.setRoundData(2_000 * 10**20, now, 20))
        self.assertEqual(self.oracle.functions.navUsd(2 * WETH).call(), 4_000 * WETH)

    def test_nav_usd_reverts_on_invalid_price_timestamp_staleness_and_unsupported_decimals(self):
        now = self._latest_timestamp()

        self._send(self.aggregator.functions.setRoundData(0, now, 8))
        self._assert_reverts(lambda: self.oracle.functions.navUsd(WETH).call())

        self._send(self.aggregator.functions.setRoundData(2_000 * 10**8, 0, 8))
        self._assert_reverts(lambda: self.oracle.functions.navUsd(WETH).call())

        self._send(self.aggregator.functions.setRoundData(2_000 * 10**8, now - 3_601, 8))
        self._assert_reverts(lambda: self.oracle.functions.navUsd(WETH).call())

        self._send(self.aggregator.functions.setRoundData(1, now, 96))
        self._assert_reverts(lambda: self.oracle.functions.navUsd(WETH).call())


if __name__ == "__main__":
    unittest.main()