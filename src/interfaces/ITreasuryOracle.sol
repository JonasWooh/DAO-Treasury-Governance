// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ITreasuryOracle {
    function latestEthUsd() external view returns (int256 answer, uint256 updatedAt, uint8 decimals);

    function isStale() external view returns (bool);

    function navUsd(uint256 wethAmount) external view returns (uint256);
}