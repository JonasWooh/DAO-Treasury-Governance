from __future__ import annotations

import unittest

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from test.support import ensure_compiled, load_artifact


TOKEN_UNIT = 10**18
MAX_SUPPLY = 1_000_000 * TOKEN_UNIT


class CampusInnovationFundTokenTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_compiled(clean=False)
        cls.artifacts = {
            "token": load_artifact("src/governance/CampusInnovationFundToken/CampusInnovationFundToken.json"),
        }

    def setUp(self) -> None:
        self.eth_tester = EthereumTester(PyEVMBackend())
        self.w3 = Web3(EthereumTesterProvider(self.eth_tester))
        self.owner = self.w3.eth.accounts[0]
        self.holder = self.w3.eth.accounts[1]

        self.token = self._deploy("token", [self.owner])

    def _deploy(self, artifact_key: str, constructor_args: list):
        artifact = self.artifacts[artifact_key]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*constructor_args).transact({"from": self.owner})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _send(self, call, sender: str | None = None):
        tx_hash = call.transact({"from": sender or self.owner})
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _assert_reverts(self, fn):
        with self.assertRaises(TransactionFailed):
            fn()

    def test_minting_tracks_remaining_supply_and_enforces_cap(self):
        self._send(self.token.functions.mint(self.holder, MAX_SUPPLY - TOKEN_UNIT))
        self.assertEqual(self.token.functions.totalSupply().call(), MAX_SUPPLY - TOKEN_UNIT)
        self.assertEqual(self.token.functions.remainingSupply().call(), TOKEN_UNIT)

        self._send(self.token.functions.mint(self.holder, TOKEN_UNIT))
        self.assertEqual(self.token.functions.totalSupply().call(), MAX_SUPPLY)
        self.assertEqual(self.token.functions.remainingSupply().call(), 0)

        self._assert_reverts(lambda: self.token.functions.mint(self.holder, 1).transact({"from": self.owner}))

    def test_delegation_activates_votes_and_preserves_past_snapshots(self):
        mint_receipt = self._send(self.token.functions.mint(self.holder, 200_000 * TOKEN_UNIT))
        mint_block = mint_receipt.blockNumber
        self.assertEqual(self.token.functions.getVotes(self.holder).call(), 0)

        self._send(self.token.functions.delegate(self.holder), sender=self.holder)
        self.assertEqual(self.token.functions.getVotes(self.holder).call(), 200_000 * TOKEN_UNIT)
        self.assertEqual(self.token.functions.getPastVotes(self.holder, mint_block).call(), 0)

        transfer_receipt = self._send(
            self.token.functions.transfer(self.owner, TOKEN_UNIT),
            sender=self.holder,
        )
        transfer_block = transfer_receipt.blockNumber
        self.assertEqual(self.token.functions.getVotes(self.holder).call(), 199_999 * TOKEN_UNIT)
        self.assertEqual(self.token.functions.getPastVotes(self.holder, transfer_block - 1).call(), 200_000 * TOKEN_UNIT)
        self.assertEqual(self.token.functions.getPastTotalSupply(transfer_block - 1).call(), 200_000 * TOKEN_UNIT)


if __name__ == "__main__":
    unittest.main()