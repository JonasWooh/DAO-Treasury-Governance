// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {IChainlinkAggregatorV3} from "../interfaces/external/IChainlinkAggregatorV3.sol";
import {ITreasuryOracle} from "../interfaces/ITreasuryOracle.sol";
import {TreasuryConstants} from "../treasury/TreasuryConstants.sol";

contract TreasuryOracle is ITreasuryOracle {
    error InvalidAggregator(address aggregator);
    error InvalidStalePriceThreshold(uint256 stalePriceThreshold);
    error InvalidOraclePrice(int256 answer);
    error InvalidOracleTimestamp(uint256 updatedAt);
    error StaleOraclePrice(uint256 updatedAt, uint256 stalePriceThreshold, uint256 currentTimestamp);
    error UnsupportedOracleDecimals(uint8 decimals);

    IChainlinkAggregatorV3 public immutable aggregator;
    uint256 public immutable helperStalePriceThreshold;
    uint8 public immutable aggregatorDecimals;

    constructor(address aggregator_, uint256 helperStalePriceThreshold_) {
        if (aggregator_ == address(0)) {
            revert InvalidAggregator(address(0));
        }
        if (helperStalePriceThreshold_ == 0) {
            revert InvalidStalePriceThreshold(helperStalePriceThreshold_);
        }

        aggregator = IChainlinkAggregatorV3(aggregator_);
        helperStalePriceThreshold = helperStalePriceThreshold_;
        aggregatorDecimals = aggregator.decimals();
    }

    function latestEthUsd() public view override returns (int256 answer, uint256 updatedAt, uint8 decimals) {
        (, answer,, updatedAt,) = aggregator.latestRoundData();
        return (answer, updatedAt, aggregator.decimals());
    }

    function isStale() external view override returns (bool) {
        (, uint256 updatedAt,) = latestEthUsd();
        if (updatedAt == 0) {
            return true;
        }

        return block.timestamp - updatedAt > helperStalePriceThreshold;
    }

    function navUsd(uint256 wethAmount) external view override returns (uint256) {
        (int256 answer, uint256 updatedAt, uint8 decimals) = latestEthUsd();
        if (answer <= 0) {
            revert InvalidOraclePrice(answer);
        }
        if (updatedAt == 0) {
            revert InvalidOracleTimestamp(updatedAt);
        }
        if (block.timestamp - updatedAt > helperStalePriceThreshold) {
            revert StaleOraclePrice(updatedAt, helperStalePriceThreshold, block.timestamp);
        }

        uint256 normalizedUsdPrice = _normalizeOracleAnswerToUsd18(uint256(answer), decimals);
        return Math.mulDiv(wethAmount, normalizedUsdPrice, 10 ** TreasuryConstants.WETH_DECIMALS);
    }

    function _normalizeOracleAnswerToUsd18(uint256 answer, uint8 oracleDecimals) internal pure returns (uint256) {
        if (oracleDecimals == TreasuryConstants.USD_DECIMALS) {
            return answer;
        }

        if (oracleDecimals < TreasuryConstants.USD_DECIMALS) {
            return answer * _tenPow(TreasuryConstants.USD_DECIMALS - oracleDecimals);
        }

        return answer / _tenPow(oracleDecimals - TreasuryConstants.USD_DECIMALS);
    }

    function _tenPow(uint8 exponent) internal pure returns (uint256 result) {
        if (exponent > TreasuryConstants.MAX_POWER_OF_TEN_EXPONENT) {
            revert UnsupportedOracleDecimals(exponent);
        }

        result = 1;
        for (uint8 index = 0; index < exponent; ++index) {
            result *= 10;
        }
    }
}