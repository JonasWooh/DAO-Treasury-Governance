// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IFundingRegistry} from "../interfaces/IFundingRegistry.sol";

contract MockFundingRegistry {
    mapping(uint256 proposalId => IFundingRegistry.Proposal) private _proposals;
    mapping(bytes32 projectId => IFundingRegistry.Project) private _projects;
    mapping(uint256 proposalId => mapping(uint8 milestoneIndex => IFundingRegistry.Milestone)) private _milestones;

    function setProposal(IFundingRegistry.Proposal calldata proposal) external {
        _proposals[proposal.proposalId] = proposal;
    }

    function setProject(IFundingRegistry.Project calldata project) external {
        _projects[project.projectId] = project;
    }

    function setMilestone(uint256 proposalId, IFundingRegistry.Milestone calldata milestone) external {
        _milestones[proposalId][milestone.index] = milestone;
    }

    function getProposal(uint256 proposalId) external view returns (IFundingRegistry.Proposal memory) {
        return _proposals[proposalId];
    }

    function getProject(bytes32 projectId) external view returns (IFundingRegistry.Project memory) {
        return _projects[projectId];
    }

    function getMilestone(
        uint256 proposalId,
        uint8 milestoneIndex
    ) external view returns (IFundingRegistry.Milestone memory) {
        return _milestones[proposalId][milestoneIndex];
    }
}
