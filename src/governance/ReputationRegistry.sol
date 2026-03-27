// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Checkpoints} from "@openzeppelin/contracts/utils/structs/Checkpoints.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";
import {Time} from "@openzeppelin/contracts/utils/types/Time.sol";

import {IReputationRegistry} from "../interfaces/IReputationRegistry.sol";

contract ReputationRegistry is IReputationRegistry, Ownable {
    using Checkpoints for Checkpoints.Trace208;

    uint256 public constant INITIAL_MEMBER_REPUTATION = 100;
    uint256 public constant MIN_REPUTATION = 0;
    uint256 public constant MAX_REPUTATION = 1_000;

    error InvalidTimelock(address timelock);
    error InvalidWorkflowExecutor(address workflowExecutor);
    error OwnershipTransferDisabled();
    error MemberAlreadyRegistered(address member);
    error MemberNotRegistered(address member);
    error ZeroMemberAddress();
    error InitialReputationOutOfRange(uint256 initialReputation);
    error NoMembershipStateChange(address member, bool active);
    error ZeroDelta();
    error UnauthorizedWorkflowExecutor(address caller);
    error FutureLookup(uint256 timepoint, uint48 currentTimepoint);

    event MemberRegistered(address indexed member, uint256 initialReputation);
    event MemberActivityUpdated(address indexed member, bool isActive);
    event ReputationDeltaApplied(
        address indexed member,
        int256 delta,
        uint256 previousReputation,
        uint256 newReputation,
        bool viaWorkflow
    );

    address public immutable workflowExecutor;

    mapping(address member => Member) private _members;
    mapping(address member => Checkpoints.Trace208) private _memberReputationCheckpoints;
    mapping(address member => Checkpoints.Trace208) private _memberActiveCheckpoints;
    Checkpoints.Trace208 private _totalActiveReputationCheckpoints;
    address[] private _memberAccounts;

    modifier onlyWorkflowExecutor() {
        if (msg.sender != workflowExecutor) {
            revert UnauthorizedWorkflowExecutor(msg.sender);
        }
        _;
    }

    constructor(address timelock, address workflowExecutor_) Ownable(timelock) {
        if (timelock == address(0)) {
            revert InvalidTimelock(address(0));
        }
        if (workflowExecutor_ == address(0)) {
            revert InvalidWorkflowExecutor(address(0));
        }

        workflowExecutor = workflowExecutor_;
    }

    function transferOwnership(address) public pure override {
        revert OwnershipTransferDisabled();
    }

    function renounceOwnership() public pure override {
        revert OwnershipTransferDisabled();
    }

    function registerMember(address member, uint256 initialReputation) external override onlyOwner {
        if (member == address(0)) {
            revert ZeroMemberAddress();
        }
        if (_members[member].isRegistered) {
            revert MemberAlreadyRegistered(member);
        }
        if (initialReputation < MIN_REPUTATION || initialReputation > MAX_REPUTATION) {
            revert InitialReputationOutOfRange(initialReputation);
        }

        _members[member] = Member({isRegistered: true, isActive: true, currentReputation: initialReputation});
        _memberAccounts.push(member);

        _writeMemberCheckpoint(member, initialReputation);
        _writeMemberActiveCheckpoint(member, true);
        _writeTotalActiveCheckpoint(_currentTotalActiveReputation() + initialReputation);

        emit MemberRegistered(member, initialReputation);
        emit MemberActivityUpdated(member, true);
    }

    function setMemberActive(address member, bool active) external override onlyOwner {
        Member storage state = _memberState(member);
        if (state.isActive == active) {
            revert NoMembershipStateChange(member, active);
        }

        state.isActive = active;
        uint256 currentTotal = _currentTotalActiveReputation();
        if (active) {
            _writeTotalActiveCheckpoint(currentTotal + state.currentReputation);
        } else {
            _writeTotalActiveCheckpoint(currentTotal - state.currentReputation);
        }
        _writeMemberActiveCheckpoint(member, active);

        emit MemberActivityUpdated(member, active);
    }

    function applyReputationDelta(address member, int256 delta) external override onlyOwner {
        _applyReputationDelta(member, delta, false);
    }

    function applyWorkflowReputationDelta(address member, int256 delta) external override onlyWorkflowExecutor {
        _applyReputationDelta(member, delta, true);
    }

    function reputationOf(address member) external view override returns (uint256) {
        return _members[member].currentReputation;
    }

    function isActiveMember(address member) external view override returns (bool) {
        Member memory state = _members[member];
        return state.isRegistered && state.isActive;
    }

    function isRegisteredMember(address member) external view override returns (bool) {
        return _members[member].isRegistered;
    }

    function getPastReputation(address member, uint256 timepoint) external view override returns (uint256) {
        return _memberReputationCheckpoints[member].upperLookupRecent(_checkedTimepoint(timepoint));
    }

    function getPastTotalReputation(uint256 timepoint) external view override returns (uint256) {
        return _totalActiveReputationCheckpoints.upperLookupRecent(_checkedTimepoint(timepoint));
    }

    function totalActiveReputation() external view override returns (uint256) {
        return _currentTotalActiveReputation();
    }

    function isActiveAt(address member, uint256 timepoint) external view override returns (bool) {
        return _memberActiveCheckpoints[member].upperLookupRecent(_checkedTimepoint(timepoint)) == 1;
    }

    function getMember(address member) external view override returns (Member memory) {
        return _members[member];
    }

    function memberCount() external view override returns (uint256) {
        return _memberAccounts.length;
    }

    function memberAtIndex(uint256 index) external view override returns (address) {
        return _memberAccounts[index];
    }

    function clock() public view returns (uint48) {
        return Time.blockNumber();
    }

    function CLOCK_MODE() public pure returns (string memory) {
        return "mode=blocknumber&from=default";
    }

    function _applyReputationDelta(address member, int256 delta, bool viaWorkflow) internal {
        if (delta == 0) {
            revert ZeroDelta();
        }

        Member storage state = _memberState(member);
        uint256 previousReputation = state.currentReputation;
        uint256 nextReputation = _clampReputation(previousReputation, delta);
        state.currentReputation = nextReputation;

        if (nextReputation != previousReputation) {
            _writeMemberCheckpoint(member, nextReputation);
            if (state.isActive) {
                uint256 currentTotal = _currentTotalActiveReputation();
                uint256 nextTotal = currentTotal - previousReputation + nextReputation;
                _writeTotalActiveCheckpoint(nextTotal);
            }
        }

        emit ReputationDeltaApplied(member, delta, previousReputation, nextReputation, viaWorkflow);
    }

    function _memberState(address member) internal view returns (Member storage) {
        if (member == address(0)) {
            revert ZeroMemberAddress();
        }
        Member storage state = _members[member];
        if (!state.isRegistered) {
            revert MemberNotRegistered(member);
        }
        return state;
    }

    function _clampReputation(uint256 currentReputation, int256 delta) internal pure returns (uint256) {
        if (delta > 0) {
            uint256 unsignedDelta = uint256(delta);
            uint256 cappedIncrease = currentReputation + unsignedDelta;
            return cappedIncrease > MAX_REPUTATION ? MAX_REPUTATION : cappedIncrease;
        }

        uint256 magnitude = uint256(-delta);
        if (magnitude >= currentReputation) {
            return MIN_REPUTATION;
        }
        return currentReputation - magnitude;
    }

    function _checkedTimepoint(uint256 timepoint) internal view returns (uint48) {
        uint48 currentTimepoint = clock();
        if (timepoint >= currentTimepoint) {
            revert FutureLookup(timepoint, currentTimepoint);
        }
        return SafeCast.toUint48(timepoint);
    }

    function _writeMemberCheckpoint(address member, uint256 reputation) internal {
        _memberReputationCheckpoints[member].push(clock(), SafeCast.toUint208(reputation));
    }

    function _writeMemberActiveCheckpoint(address member, bool isActive) internal {
        _memberActiveCheckpoints[member].push(clock(), isActive ? 1 : 0);
    }

    function _writeTotalActiveCheckpoint(uint256 totalReputation) internal {
        _totalActiveReputationCheckpoints.push(clock(), SafeCast.toUint208(totalReputation));
    }

    function _currentTotalActiveReputation() internal view returns (uint256) {
        return _totalActiveReputationCheckpoints.latest();
    }
}
