// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IInnovationGovernor {
    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) external returns (uint256 proposalId);

    function castVote(uint256 proposalId, uint8 support) external returns (uint256 weight);

    function queue(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) external returns (uint256 proposalId);

    function execute(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    ) external payable returns (uint256 proposalId);
}
