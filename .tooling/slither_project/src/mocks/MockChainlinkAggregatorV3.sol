// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IChainlinkAggregatorV3} from "../interfaces/external/IChainlinkAggregatorV3.sol";

contract MockChainlinkAggregatorV3 is IChainlinkAggregatorV3 {
    int256 private _answer;
    uint256 private _updatedAt;
    uint8 private _decimals;
    uint80 private _roundId;

    constructor() {
        _decimals = 8;
    }

    function setRoundData(int256 answer, uint256 updatedAt, uint8 decimals_) external {
        _roundId += 1;
        _answer = answer;
        _updatedAt = updatedAt;
        _decimals = decimals_;
    }

    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    function latestRoundData()
        external
        view
        override
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    {
        return (_roundId, _answer, _updatedAt, _updatedAt, _roundId);
    }
}