// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IAaveWethAdapter} from "../interfaces/IAaveWethAdapter.sol";
import {IAaveV3Pool} from "../interfaces/external/IAaveV3Pool.sol";

contract AaveWethAdapter is IAaveWethAdapter {
    using SafeERC20 for IERC20;

    error InvalidTreasury(address treasury);
    error InvalidWeth(address weth);
    error InvalidPool(address pool);
    error InvalidAToken(address aToken);
    error UnauthorizedCaller(address caller);
    error ZeroAmount();
    error TreasuryPullMismatch(uint256 expectedIncreaseWeth, uint256 actualIncreaseWeth);
    error SupplyPoolPullMismatch(uint256 expectedAdapterBalanceWeth, uint256 actualAdapterBalanceWeth);
    error SupplyBalanceMismatch(uint256 expectedIncreaseWeth, uint256 actualIncreaseWeth);
    error WithdrawReturnMismatch(uint256 expectedWithdrawWeth, uint256 actualWithdrawWeth);
    error TreasuryCreditMismatch(uint256 expectedIncreaseWeth, uint256 actualIncreaseWeth);
    error WithdrawBalanceMismatch(uint256 expectedDecreaseWeth, uint256 actualDecreaseWeth);

    uint16 internal constant AAVE_REFERRAL_CODE = 0;

    address public immutable treasury;
    IERC20 public immutable wethToken;
    IAaveV3Pool public immutable pool;
    IERC20 public immutable aToken;

    modifier onlyTreasury() {
        if (msg.sender != treasury) {
            revert UnauthorizedCaller(msg.sender);
        }
        _;
    }

    constructor(address treasury_, address weth, address pool_, address aToken_) {
        if (treasury_ == address(0)) {
            revert InvalidTreasury(address(0));
        }
        if (weth == address(0)) {
            revert InvalidWeth(address(0));
        }
        if (pool_ == address(0)) {
            revert InvalidPool(address(0));
        }
        if (aToken_ == address(0)) {
            revert InvalidAToken(address(0));
        }

        treasury = treasury_;
        wethToken = IERC20(weth);
        pool = IAaveV3Pool(pool_);
        aToken = IERC20(aToken_);
    }

    function supply(uint256 amountWeth) external override onlyTreasury {
        if (amountWeth == 0) {
            revert ZeroAmount();
        }

        uint256 adapterWethBefore = wethToken.balanceOf(address(this));
        uint256 aTokenBefore = aToken.balanceOf(address(this));

        wethToken.safeTransferFrom(treasury, address(this), amountWeth);

        uint256 adapterWethAfterPull = wethToken.balanceOf(address(this));
        uint256 actualPulledWeth = adapterWethAfterPull - adapterWethBefore;
        if (actualPulledWeth != amountWeth) {
            revert TreasuryPullMismatch(amountWeth, actualPulledWeth);
        }

        wethToken.forceApprove(address(pool), amountWeth);
        pool.supply(address(wethToken), amountWeth, address(this), AAVE_REFERRAL_CODE);
        wethToken.forceApprove(address(pool), 0);

        uint256 adapterWethAfterSupply = wethToken.balanceOf(address(this));
        if (adapterWethAfterSupply != adapterWethBefore) {
            revert SupplyPoolPullMismatch(adapterWethBefore, adapterWethAfterSupply);
        }

        uint256 actualATokenIncrease = aToken.balanceOf(address(this)) - aTokenBefore;
        if (actualATokenIncrease != amountWeth) {
            revert SupplyBalanceMismatch(amountWeth, actualATokenIncrease);
        }
    }

    function withdraw(uint256 amountWeth) external override onlyTreasury {
        if (amountWeth == 0) {
            revert ZeroAmount();
        }

        uint256 treasuryWethBefore = wethToken.balanceOf(treasury);
        uint256 aTokenBefore = aToken.balanceOf(address(this));

        uint256 withdrawnWeth = pool.withdraw(address(wethToken), amountWeth, treasury);
        if (withdrawnWeth != amountWeth) {
            revert WithdrawReturnMismatch(amountWeth, withdrawnWeth);
        }

        uint256 treasuryWethAfter = wethToken.balanceOf(treasury);
        if (treasuryWethAfter < treasuryWethBefore) {
            revert TreasuryCreditMismatch(amountWeth, 0);
        }

        uint256 actualTreasuryIncrease = treasuryWethAfter - treasuryWethBefore;
        if (actualTreasuryIncrease != amountWeth) {
            revert TreasuryCreditMismatch(amountWeth, actualTreasuryIncrease);
        }

        uint256 aTokenAfter = aToken.balanceOf(address(this));
        if (aTokenAfter > aTokenBefore) {
            revert WithdrawBalanceMismatch(amountWeth, 0);
        }

        uint256 actualATokenDecrease = aTokenBefore - aTokenAfter;
        if (actualATokenDecrease != amountWeth) {
            revert WithdrawBalanceMismatch(amountWeth, actualATokenDecrease);
        }
    }

    function suppliedBalance() external view override returns (uint256) {
        return aToken.balanceOf(address(this));
    }
}