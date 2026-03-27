// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ICampusInnovationFundToken {
    function mint(address to, uint256 amount) external;
    function delegate(address delegatee) external;
    function getVotes(address account) external view returns (uint256);
    function getPastVotes(address account, uint256 timepoint) external view returns (uint256);
    function getPastTotalSupply(uint256 timepoint) external view returns (uint256);
    function maxSupply() external pure returns (uint256);
    function remainingSupply() external view returns (uint256);
}
