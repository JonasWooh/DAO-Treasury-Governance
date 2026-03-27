// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract GovernedActionTarget is Ownable {
    uint256 public trackedValue;
    bytes32 public trackedHash;

    event TrackedValueUpdated(uint256 previousValue, uint256 newValue);
    event TrackedHashUpdated(bytes32 previousHash, bytes32 newHash);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function setTrackedValue(uint256 newValue) external onlyOwner {
        uint256 previousValue = trackedValue;
        trackedValue = newValue;
        emit TrackedValueUpdated(previousValue, newValue);
    }

    function setTrackedHash(bytes32 newHash) external onlyOwner {
        bytes32 previousHash = trackedHash;
        trackedHash = newHash;
        emit TrackedHashUpdated(previousHash, newHash);
    }
}
