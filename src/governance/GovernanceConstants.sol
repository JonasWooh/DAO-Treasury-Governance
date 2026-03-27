// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library GovernanceConstants {
    string internal constant TOKEN_NAME = "Campus Innovation Fund Token";
    string internal constant TOKEN_SYMBOL = "CIF";

    uint256 internal constant TOKEN_UNIT = 1 ether;
    uint256 internal constant CIF_TOTAL_SUPPLY = 1_000_000 * TOKEN_UNIT;
    uint256 internal constant INITIAL_VOTER_ALLOCATION = 200_000 * TOKEN_UNIT;
    uint256 internal constant INITIAL_GOVERNANCE_RESERVE = 400_000 * TOKEN_UNIT;

    uint48 internal constant VOTING_DELAY_BLOCKS = 1;
    uint32 internal constant VOTING_PERIOD_BLOCKS = 20;
    uint256 internal constant PROPOSAL_THRESHOLD = 10_000 * TOKEN_UNIT;
    uint256 internal constant QUORUM_NUMERATOR = 4;
    uint256 internal constant TIMELOCK_MIN_DELAY_SECONDS = 120;
}
