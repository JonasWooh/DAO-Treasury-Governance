// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IAaveWethAdapter} from "../interfaces/IAaveWethAdapter.sol";
import {IInnovationTreasury} from "../interfaces/IInnovationTreasury.sol";
import {ITreasuryOracle} from "../interfaces/ITreasuryOracle.sol";
import {TreasuryConstants} from "./TreasuryConstants.sol";

contract InnovationTreasury is IInnovationTreasury, Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    error InvalidWeth(address weth);
    error InvalidOracle(address oracle);
    error InvalidAaveAdapter(address aaveAdapter);
    error OwnershipTransferDisabled();
    error InvalidProjectId(bytes32 projectId);
    error ProjectIdAlreadyUsed(bytes32 projectId);
    error InvalidProjectRecipient(address recipient);
    error InvalidProjectBudget(uint256 maxBudgetWeth);
    error InvalidMilestoneCount(uint8 milestoneCount);
    error InvalidMilestoneAmount(uint256 amountWeth);
    error ProjectNotActive(bytes32 projectId);
    error InvalidMilestoneIndex(bytes32 projectId, uint8 expectedIndex, uint8 actualIndex);
    error ProjectBudgetExceeded(bytes32 projectId, uint256 requestedTotal, uint256 maxBudgetWeth);
    error GrantBudgetExceedsLimit(uint256 requestedBudgetWeth, uint256 allowedBudgetWeth);
    error ZeroAmount();
    error InsufficientLiquidWeth(uint256 availableLiquidWeth, uint256 requiredWeth);
    error ReserveFloorBreached(uint256 liquidAfterWeth, uint256 requiredLiquidWeth);
    error InvalidPolicyBps(uint256 bpsValue);
    error InvalidStalePriceThreshold(uint256 stalePriceThreshold);
    error InvalidOraclePrice(int256 answer);
    error InvalidOracleTimestamp(uint256 updatedAt);
    error StaleOraclePrice(uint256 updatedAt, uint256 stalePriceThreshold, uint256 currentTimestamp);
    error UnsupportedOracleDecimals(uint8 decimals);
    error AdapterSupplyMismatch(uint256 expectedDecreaseWeth, uint256 actualDecreaseWeth);
    error AdapterWithdrawMismatch(uint256 expectedIncreaseWeth, uint256 actualIncreaseWeth);

    event ProjectApproved(
        bytes32 indexed projectId,
        address indexed recipient,
        uint256 maxBudgetWeth,
        uint8 milestoneCount
    );
    event MilestoneReleased(
        bytes32 indexed projectId,
        uint8 indexed milestoneIndex,
        address indexed recipient,
        uint256 amountWeth,
        uint256 totalReleasedWeth,
        bool projectCompleted
    );
    event IdleFundsDeposited(uint256 amountWeth, uint256 liquidBalanceAfterWeth, uint256 suppliedBalanceAfterWeth);
    event IdleFundsWithdrawn(uint256 amountWeth, uint256 liquidBalanceAfterWeth, uint256 suppliedBalanceAfterWeth);
    event RiskPolicyUpdated(uint256 minLiquidReserveBps, uint256 maxSingleGrantBps, uint256 stalePriceThreshold);

    IERC20 public immutable wethToken;
    ITreasuryOracle public immutable treasuryOracle;
    IAaveWethAdapter public immutable aaveWethAdapter;

    mapping(bytes32 projectId => Project) private _projects;
    mapping(bytes32 projectId => bool) public projectIdUsed;

    uint256 private _minLiquidReserveBps;
    uint256 private _maxSingleGrantBps;
    uint256 private _stalePriceThreshold;

    constructor(address timelock, address weth, address oracle, address aaveAdapter) Ownable(timelock) {
        if (weth == address(0)) {
            revert InvalidWeth(address(0));
        }
        if (oracle == address(0)) {
            revert InvalidOracle(address(0));
        }
        if (aaveAdapter == address(0)) {
            revert InvalidAaveAdapter(address(0));
        }

        wethToken = IERC20(weth);
        treasuryOracle = ITreasuryOracle(oracle);
        aaveWethAdapter = IAaveWethAdapter(aaveAdapter);

        _minLiquidReserveBps = TreasuryConstants.DEFAULT_MIN_LIQUID_RESERVE_BPS;
        _maxSingleGrantBps = TreasuryConstants.DEFAULT_MAX_SINGLE_GRANT_BPS;
        _stalePriceThreshold = TreasuryConstants.DEFAULT_STALE_PRICE_THRESHOLD;
    }

    function transferOwnership(address) public pure override {
        revert OwnershipTransferDisabled();
    }

    function renounceOwnership() public pure override {
        revert OwnershipTransferDisabled();
    }

    function approveProject(bytes32 projectId, address recipient, uint256 maxBudgetWeth, uint8 milestoneCount)
        external
        override
        onlyOwner
    {
        if (projectId == bytes32(0)) {
            revert InvalidProjectId(projectId);
        }
        if (projectIdUsed[projectId]) {
            revert ProjectIdAlreadyUsed(projectId);
        }
        if (recipient == address(0)) {
            revert InvalidProjectRecipient(recipient);
        }
        if (maxBudgetWeth == 0) {
            revert InvalidProjectBudget(maxBudgetWeth);
        }
        if (milestoneCount == 0) {
            revert InvalidMilestoneCount(milestoneCount);
        }

        uint256 allowedBudgetWeth = Math.mulDiv(totalManagedWeth(), _maxSingleGrantBps, TreasuryConstants.BPS_DENOMINATOR);
        if (maxBudgetWeth > allowedBudgetWeth) {
            revert GrantBudgetExceedsLimit(maxBudgetWeth, allowedBudgetWeth);
        }

        _projects[projectId] = Project({
            recipient: recipient,
            maxBudgetWeth: maxBudgetWeth,
            releasedWeth: 0,
            milestoneCount: milestoneCount,
            milestonesReleased: 0,
            active: true
        });
        projectIdUsed[projectId] = true;

        emit ProjectApproved(projectId, recipient, maxBudgetWeth, milestoneCount);
    }

    function releaseMilestone(bytes32 projectId, uint8 milestoneIndex, uint256 amountWeth) external override onlyOwner nonReentrant {
        Project storage project = _projects[projectId];
        if (!project.active) {
            revert ProjectNotActive(projectId);
        }
        if (milestoneIndex != project.milestonesReleased) {
            revert InvalidMilestoneIndex(projectId, project.milestonesReleased, milestoneIndex);
        }
        if (amountWeth == 0) {
            revert InvalidMilestoneAmount(amountWeth);
        }

        uint256 newReleasedTotal = project.releasedWeth + amountWeth;
        if (newReleasedTotal > project.maxBudgetWeth) {
            revert ProjectBudgetExceeded(projectId, newReleasedTotal, project.maxBudgetWeth);
        }

        uint256 liquidBalance = liquidWethBalance();
        if (liquidBalance < amountWeth) {
            revert InsufficientLiquidWeth(liquidBalance, amountWeth);
        }

        project.releasedWeth = newReleasedTotal;
        project.milestonesReleased += 1;

        bool completed = project.milestonesReleased == project.milestoneCount;
        if (completed) {
            project.active = false;
        }

        wethToken.safeTransfer(project.recipient, amountWeth);

        emit MilestoneReleased(
            projectId,
            milestoneIndex,
            project.recipient,
            amountWeth,
            project.releasedWeth,
            completed
        );
    }

    function depositIdleFunds(uint256 amountWeth) external override onlyOwner nonReentrant {
        if (amountWeth == 0) {
            revert ZeroAmount();
        }

        uint256 liquidBefore = liquidWethBalance();
        if (amountWeth > liquidBefore) {
            revert InsufficientLiquidWeth(liquidBefore, amountWeth);
        }

        uint256 suppliedBefore = suppliedWethBalance();
        uint256 totalManagedBefore = liquidBefore + suppliedBefore;
        uint256 liquidAfter = liquidBefore - amountWeth;
        uint256 requiredLiquid = Math.mulDiv(
            totalManagedBefore,
            _minLiquidReserveBps,
            TreasuryConstants.BPS_DENOMINATOR,
            Math.Rounding.Ceil
        );
        if (liquidAfter < requiredLiquid) {
            revert ReserveFloorBreached(liquidAfter, requiredLiquid);
        }

        wethToken.forceApprove(address(aaveWethAdapter), amountWeth);
        aaveWethAdapter.supply(amountWeth);
        wethToken.forceApprove(address(aaveWethAdapter), 0);

        uint256 liquidAfterObserved = liquidWethBalance();
        uint256 actualDecreaseWeth = liquidBefore - liquidAfterObserved;
        if (actualDecreaseWeth != amountWeth) {
            revert AdapterSupplyMismatch(amountWeth, actualDecreaseWeth);
        }

        uint256 suppliedAfter = totalManagedBefore - liquidAfterObserved;

        emit IdleFundsDeposited(amountWeth, liquidAfterObserved, suppliedAfter);
    }

    function withdrawIdleFunds(uint256 amountWeth) external override onlyOwner nonReentrant {
        if (amountWeth == 0) {
            revert ZeroAmount();
        }

        uint256 liquidBefore = liquidWethBalance();
        uint256 suppliedBefore = suppliedWethBalance();
        aaveWethAdapter.withdraw(amountWeth);
        uint256 liquidAfter = liquidWethBalance();
        if (liquidAfter < liquidBefore) {
            revert AdapterWithdrawMismatch(amountWeth, 0);
        }

        uint256 actualIncreaseWeth = liquidAfter - liquidBefore;
        if (actualIncreaseWeth != amountWeth) {
            revert AdapterWithdrawMismatch(amountWeth, actualIncreaseWeth);
        }

        uint256 suppliedAfter = suppliedBefore - amountWeth;

        emit IdleFundsWithdrawn(amountWeth, liquidAfter, suppliedAfter);
    }

    function setRiskPolicy(uint256 minLiquidReserveBps, uint256 maxSingleGrantBps, uint256 stalePriceThreshold)
        external
        override
        onlyOwner
    {
        if (minLiquidReserveBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidPolicyBps(minLiquidReserveBps);
        }
        if (maxSingleGrantBps > TreasuryConstants.BPS_DENOMINATOR) {
            revert InvalidPolicyBps(maxSingleGrantBps);
        }
        if (stalePriceThreshold == 0) {
            revert InvalidStalePriceThreshold(stalePriceThreshold);
        }

        _minLiquidReserveBps = minLiquidReserveBps;
        _maxSingleGrantBps = maxSingleGrantBps;
        _stalePriceThreshold = stalePriceThreshold;

        emit RiskPolicyUpdated(minLiquidReserveBps, maxSingleGrantBps, stalePriceThreshold);
    }

    function navUsd() external view override returns (uint256) {
        (int256 answer, uint256 updatedAt, uint8 oracleDecimals) = treasuryOracle.latestEthUsd();
        if (answer <= 0) {
            revert InvalidOraclePrice(answer);
        }
        if (updatedAt == 0) {
            revert InvalidOracleTimestamp(updatedAt);
        }
        if (block.timestamp - updatedAt > _stalePriceThreshold) {
            revert StaleOraclePrice(updatedAt, _stalePriceThreshold, block.timestamp);
        }

        uint256 normalizedUsdPrice = _normalizeOracleAnswerToUsd18(uint256(answer), oracleDecimals);
        return Math.mulDiv(totalManagedWeth(), normalizedUsdPrice, 10 ** TreasuryConstants.WETH_DECIMALS);
    }

    function getProject(bytes32 projectId) external view override returns (Project memory) {
        return _projects[projectId];
    }

    function liquidWethBalance() public view override returns (uint256) {
        return wethToken.balanceOf(address(this));
    }

    function suppliedWethBalance() public view override returns (uint256) {
        return aaveWethAdapter.suppliedBalance();
    }

    function totalManagedWeth() public view override returns (uint256) {
        return liquidWethBalance() + suppliedWethBalance();
    }

    function riskPolicy()
        external
        view
        override
        returns (uint256 minLiquidReserveBps, uint256 maxSingleGrantBps, uint256 stalePriceThreshold)
    {
        return (_minLiquidReserveBps, _maxSingleGrantBps, _stalePriceThreshold);
    }

    function _normalizeOracleAnswerToUsd18(uint256 answer, uint8 oracleDecimals) internal pure returns (uint256) {
        if (oracleDecimals == TreasuryConstants.USD_DECIMALS) {
            return answer;
        }

        if (oracleDecimals < TreasuryConstants.USD_DECIMALS) {
            uint8 factor = TreasuryConstants.USD_DECIMALS - oracleDecimals;
            return answer * _tenPow(factor);
        }

        uint8 divisorFactor = oracleDecimals - TreasuryConstants.USD_DECIMALS;
        return answer / _tenPow(divisorFactor);
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