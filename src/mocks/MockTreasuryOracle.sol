// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {ITreasuryOracle} from "../interfaces/ITreasuryOracle.sol";
import {TreasuryConstants} from "../treasury/TreasuryConstants.sol";

contract MockTreasuryOracle is ITreasuryOracle {
    int256 private _answer;
    uint256 private _updatedAt;
    uint8 private _decimals;
    uint256 private _staleThreshold;

    constructor() {
        _decimals = 8;
        _staleThreshold = TreasuryConstants.DEFAULT_STALE_PRICE_THRESHOLD;
    }

    function setPrice(int256 answer, uint256 updatedAt, uint8 decimals_) external {
        _answer = answer;
        _updatedAt = updatedAt;
        _decimals = decimals_;
    }

    function setStaleThreshold(uint256 staleThreshold_) external {
        _staleThreshold = staleThreshold_;
    }

    function latestEthUsd() external view override returns (int256 answer, uint256 updatedAt, uint8 decimals) {
        return (_answer, _updatedAt, _decimals);
    }

    function isStale() external view override returns (bool) {
        if (_updatedAt == 0) {
            return true;
        }
        return block.timestamp - _updatedAt > _staleThreshold;
    }

    function navUsd(uint256 wethAmount) external view override returns (uint256) {
        require(_answer > 0, "invalid answer");

        uint256 normalizedAnswer = uint256(_answer);
        if (_decimals < TreasuryConstants.USD_DECIMALS) {
            normalizedAnswer *= 10 ** (TreasuryConstants.USD_DECIMALS - _decimals);
        } else if (_decimals > TreasuryConstants.USD_DECIMALS) {
            normalizedAnswer /= 10 ** (_decimals - TreasuryConstants.USD_DECIMALS);
        }

        return Math.mulDiv(wethAmount, normalizedAnswer, 10 ** TreasuryConstants.WETH_DECIMALS);
    }
}