// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IInnovationTreasury {
    struct Project {
        address recipient;
        uint256 maxBudgetWeth;
        uint256 releasedWeth;
        uint8 milestoneCount;
        uint8 milestonesReleased;
        bool active;
    }

    function approveProject(bytes32 projectId, address recipient, uint256 maxBudgetWeth, uint8 milestoneCount) external;

    function releaseMilestone(bytes32 projectId, uint8 milestoneIndex, uint256 amountWeth) external;

    function depositIdleFunds(uint256 amountWeth) external;

    function withdrawIdleFunds(uint256 amountWeth) external;

    function setRiskPolicy(uint256 minLiquidReserveBps, uint256 maxSingleGrantBps, uint256 stalePriceThreshold)
        external;

    function navUsd() external view returns (uint256);

    function getProject(bytes32 projectId) external view returns (Project memory);

    function liquidWethBalance() external view returns (uint256);

    function suppliedWethBalance() external view returns (uint256);

    function totalManagedWeth() external view returns (uint256);

    function riskPolicy()
        external
        view
        returns (uint256 minLiquidReserveBps, uint256 maxSingleGrantBps, uint256 stalePriceThreshold);
}