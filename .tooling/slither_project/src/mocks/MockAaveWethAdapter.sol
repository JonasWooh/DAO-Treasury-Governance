// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {IAaveWethAdapter} from "../interfaces/IAaveWethAdapter.sol";
import {TreasuryConstants} from "../treasury/TreasuryConstants.sol";

contract MockAaveWethAdapter is IAaveWethAdapter {
    using SafeERC20 for IERC20;

    error InvalidBps(uint256 bpsValue);
    error InsufficientSuppliedBalance(uint256 suppliedBalanceWeth, uint256 requestedWeth);

    IERC20 public immutable wethToken;

    uint256 private _suppliedBalance;
    uint256 public supplyPullBps;
    uint256 public withdrawReturnBps;

    constructor(address weth) {
        wethToken = IERC20(weth);
        supplyPullBps = TreasuryConstants.BPS_DENOMINATOR;
        withdrawReturnBps = TreasuryConstants.BPS_DENOMINATOR;
    }

    function setSupplyPullBps(uint256 newSupplyPullBps) external {
        if (newSupplyPullBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newSupplyPullBps);
        }
        supplyPullBps = newSupplyPullBps;
    }

    function setWithdrawReturnBps(uint256 newWithdrawReturnBps) external {
        if (newWithdrawReturnBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newWithdrawReturnBps);
        }
        withdrawReturnBps = newWithdrawReturnBps;
    }

    function supply(uint256 amountWeth) external override {
        uint256 actualPullWeth = Math.mulDiv(amountWeth, supplyPullBps, TreasuryConstants.BPS_DENOMINATOR);
        if (actualPullWeth > 0) {
            wethToken.safeTransferFrom(msg.sender, address(this), actualPullWeth);
            _suppliedBalance += actualPullWeth;
        }
    }

    function withdraw(uint256 amountWeth) external override {
        uint256 actualReturnWeth = Math.mulDiv(amountWeth, withdrawReturnBps, TreasuryConstants.BPS_DENOMINATOR);
        if (actualReturnWeth > _suppliedBalance) {
            revert InsufficientSuppliedBalance(_suppliedBalance, actualReturnWeth);
        }

        _suppliedBalance -= actualReturnWeth;
        if (actualReturnWeth > 0) {
            wethToken.safeTransfer(msg.sender, actualReturnWeth);
        }
    }

    function suppliedBalance() external view override returns (uint256) {
        return _suppliedBalance;
    }
}