// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {IAaveV3Pool} from "../interfaces/external/IAaveV3Pool.sol";
import {TreasuryConstants} from "../treasury/TreasuryConstants.sol";
import {MockAToken} from "./MockAToken.sol";

interface IMockMintableErc20 is IERC20 {
    function mint(address to, uint256 amount) external;
}

contract MockAavePool is IAaveV3Pool {
    using SafeERC20 for IERC20;

    error InvalidWeth(address weth);
    error InvalidAsset(address asset);
    error InvalidBps(uint256 bpsValue);
    error InsufficientATokenBalance(uint256 availableATokenWeth, uint256 requestedATokenWeth);

    IERC20 public immutable wethToken;
    MockAToken public immutable aToken;

    uint256 public supplyPullBps;
    uint256 public supplyMintBps;
    uint256 public withdrawReturnBps;
    uint256 public withdrawTransferBps;

    constructor(address weth) {
        if (weth == address(0)) {
            revert InvalidWeth(address(0));
        }

        wethToken = IERC20(weth);
        aToken = new MockAToken(address(this));
        supplyPullBps = TreasuryConstants.BPS_DENOMINATOR;
        supplyMintBps = TreasuryConstants.BPS_DENOMINATOR;
        withdrawReturnBps = TreasuryConstants.BPS_DENOMINATOR;
        withdrawTransferBps = TreasuryConstants.BPS_DENOMINATOR;
    }

    function setSupplyPullBps(uint256 newSupplyPullBps) external {
        if (newSupplyPullBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newSupplyPullBps);
        }

        supplyPullBps = newSupplyPullBps;
    }

    function setSupplyMintBps(uint256 newSupplyMintBps) external {
        if (newSupplyMintBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newSupplyMintBps);
        }

        supplyMintBps = newSupplyMintBps;
    }

    function setWithdrawReturnBps(uint256 newWithdrawReturnBps) external {
        if (newWithdrawReturnBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newWithdrawReturnBps);
        }

        withdrawReturnBps = newWithdrawReturnBps;
    }

    function setWithdrawTransferBps(uint256 newWithdrawTransferBps) external {
        if (newWithdrawTransferBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidBps(newWithdrawTransferBps);
        }

        withdrawTransferBps = newWithdrawTransferBps;
    }

    function accrueYield(address onBehalfOf, uint256 amountWeth) external {
        if (amountWeth == 0) {
            return;
        }

        IMockMintableErc20(address(wethToken)).mint(address(this), amountWeth);
        aToken.mint(onBehalfOf, amountWeth);
    }

    function supply(address asset, uint256 amount, address onBehalfOf, uint16) external override {
        if (asset != address(wethToken)) {
            revert InvalidAsset(asset);
        }

        uint256 pulledWeth = Math.mulDiv(amount, supplyPullBps, TreasuryConstants.BPS_DENOMINATOR);
        if (pulledWeth > 0) {
            wethToken.safeTransferFrom(msg.sender, address(this), pulledWeth);
        }

        uint256 mintedAToken = Math.mulDiv(amount, supplyMintBps, TreasuryConstants.BPS_DENOMINATOR);
        if (mintedAToken > 0) {
            aToken.mint(onBehalfOf, mintedAToken);
        }
    }

    function withdraw(address asset, uint256 amount, address to) external override returns (uint256) {
        if (asset != address(wethToken)) {
            revert InvalidAsset(asset);
        }

        uint256 availableATokenWeth = aToken.balanceOf(msg.sender);
        if (availableATokenWeth < amount) {
            revert InsufficientATokenBalance(availableATokenWeth, amount);
        }

        aToken.burn(msg.sender, amount);

        uint256 transferredWeth = Math.mulDiv(amount, withdrawTransferBps, TreasuryConstants.BPS_DENOMINATOR);
        if (transferredWeth > 0) {
            wethToken.safeTransfer(to, transferredWeth);
        }

        return Math.mulDiv(amount, withdrawReturnBps, TreasuryConstants.BPS_DENOMINATOR);
    }
}