// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Governor} from "@openzeppelin/contracts/governance/Governor.sol";
import {GovernorCountingSimple} from "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {GovernorSettings} from "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import {GovernorTimelockControl} from "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import {GovernorVotes} from "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorVotesQuorumFraction} from "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {IVotes} from "@openzeppelin/contracts/governance/utils/IVotes.sol";

import {IInnovationGovernor} from "../interfaces/IInnovationGovernor.sol";
import {GovernanceConstants} from "./GovernanceConstants.sol";

contract InnovationGovernor is
    IInnovationGovernor,
    Governor,
    GovernorSettings,
    GovernorCountingSimple,
    GovernorVotes,
    GovernorVotesQuorumFraction,
    GovernorTimelockControl
{
    error InvalidVotesToken(address token);
    error InvalidTimelock(address timelock);

    constructor(IVotes token_, TimelockController timelock_)
        Governor("InnovationGovernor")
        GovernorSettings(
            GovernanceConstants.VOTING_DELAY_BLOCKS,
            GovernanceConstants.VOTING_PERIOD_BLOCKS,
            GovernanceConstants.PROPOSAL_THRESHOLD
        )
        GovernorVotes(token_)
        GovernorVotesQuorumFraction(GovernanceConstants.QUORUM_NUMERATOR)
        GovernorTimelockControl(timelock_)
    {
        if (address(token_) == address(0)) {
            revert InvalidVotesToken(address(0));
        }

        if (address(timelock_) == address(0)) {
            revert InvalidTimelock(address(0));
        }
    }

    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) public override(IInnovationGovernor, Governor) returns (uint256 proposalId) {
        return super.propose(targets, values, calldatas, description);
    }

    function castVote(
        uint256 proposalId,
        uint8 support
    ) public override(IInnovationGovernor, Governor) returns (uint256 weight) {
        return super.castVote(proposalId, support);
    }

    function queue(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) public override(IInnovationGovernor, Governor) returns (uint256 proposalId) {
        return super.queue(targets, values, calldatas, descriptionHash);
    }

    function execute(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) public payable override(IInnovationGovernor, Governor) returns (uint256 proposalId) {
        return super.execute(targets, values, calldatas, descriptionHash);
    }

    function quorum(uint256 timepoint) public view override(Governor, GovernorVotesQuorumFraction) returns (uint256) {
        return super.quorum(timepoint);
    }

    function state(uint256 proposalId) public view override(Governor, GovernorTimelockControl) returns (ProposalState) {
        return super.state(proposalId);
    }

    function proposalThreshold() public view override(Governor, GovernorSettings) returns (uint256) {
        return super.proposalThreshold();
    }

    function proposalNeedsQueuing(
        uint256 proposalId
    ) public view override(Governor, GovernorTimelockControl) returns (bool) {
        return super.proposalNeedsQueuing(proposalId);
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint48) {
        return super._queueOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) {
        super._executeOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) internal override(Governor, GovernorTimelockControl) returns (uint256) {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    function _executor() internal view override(Governor, GovernorTimelockControl) returns (address) {
        return super._executor();
    }
}