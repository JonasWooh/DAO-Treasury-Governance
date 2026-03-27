// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IGovernor} from "@openzeppelin/contracts/governance/IGovernor.sol";

contract MockInnovationGovernor {
    mapping(uint256 proposalId => IGovernor.ProposalState) private _proposalStates;
    mapping(uint256 proposalId => mapping(address voter => bool hasVoted_)) private _hasVoted;

    function setProposalState(uint256 proposalId, IGovernor.ProposalState proposalState) external {
        _proposalStates[proposalId] = proposalState;
    }

    function setHasVoted(uint256 proposalId, address voter, bool hasVoted_) external {
        _hasVoted[proposalId][voter] = hasVoted_;
    }

    function state(uint256 proposalId) external view returns (IGovernor.ProposalState) {
        return _proposalStates[proposalId];
    }

    function hasVoted(uint256 proposalId, address voter) external view returns (bool) {
        return _hasVoted[proposalId][voter];
    }
}
