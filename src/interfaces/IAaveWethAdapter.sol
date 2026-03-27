// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAaveWethAdapter {
    function supply(uint256 amountWeth) external;

    function withdraw(uint256 amountWeth) external;

    function suppliedBalance() external view returns (uint256);
}