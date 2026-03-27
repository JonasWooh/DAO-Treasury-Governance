// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IReputationRegistry {
    struct Member {
        bool isRegistered;
        bool isActive;
        uint256 currentReputation;
    }

    function registerMember(address member, uint256 initialReputation) external;

    function setMemberActive(address member, bool active) external;

    function applyReputationDelta(address member, int256 delta) external;

    function applyWorkflowReputationDelta(address member, int256 delta) external;

    function reputationOf(address member) external view returns (uint256);

    function isActiveMember(address member) external view returns (bool);

    function isRegisteredMember(address member) external view returns (bool);

    function getPastReputation(address member, uint256 timepoint) external view returns (uint256);

    function getPastTotalReputation(uint256 timepoint) external view returns (uint256);

    function totalActiveReputation() external view returns (uint256);

    function isActiveAt(address member, uint256 timepoint) external view returns (bool);

    function getMember(address member) external view returns (Member memory);

    function memberCount() external view returns (uint256);

    function memberAtIndex(uint256 index) external view returns (address);
}
