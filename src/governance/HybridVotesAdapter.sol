// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Time} from "@openzeppelin/contracts/utils/types/Time.sol";
import {IERC5805} from "@openzeppelin/contracts/interfaces/IERC5805.sol";

import {IReputationRegistry} from "../interfaces/IReputationRegistry.sol";

contract HybridVotesAdapter is IERC5805 {
    uint256 public constant TOKEN_WEIGHT_BPS = 6_000;
    uint256 public constant REPUTATION_WEIGHT_BPS = 4_000;
    uint256 public constant WEIGHT_DENOMINATOR = 10_000;

    error InvalidVotesToken(address token);
    error InvalidReputationRegistry(address reputationRegistry);
    error DelegationMustBePerformedOnToken();

    IERC5805 public immutable votesToken;
    IReputationRegistry public immutable reputationRegistry;

    constructor(address token, address reputationRegistry_) {
        if (token == address(0)) {
            revert InvalidVotesToken(address(0));
        }
        if (reputationRegistry_ == address(0)) {
            revert InvalidReputationRegistry(address(0));
        }

        votesToken = IERC5805(token);
        reputationRegistry = IReputationRegistry(reputationRegistry_);
    }

    function getVotes(address account) public view override returns (uint256) {
        uint256 tokenVotes = votesToken.getVotes(account);
        uint256 currentTotalSupply = IERC20(address(votesToken)).totalSupply();
        IReputationRegistry.Member memory memberState = reputationRegistry.getMember(account);
        uint256 currentReputation = memberState.isActive ? memberState.currentReputation : 0;
        uint256 currentTotalReputation = reputationRegistry.totalActiveReputation();

        return _hybridVotes(tokenVotes, currentReputation, currentTotalReputation, currentTotalSupply);
    }

    function getPastVotes(address account, uint256 timepoint) public view override returns (uint256) {
        uint256 tokenVotes = votesToken.getPastVotes(account, timepoint);
        uint256 totalSupply = votesToken.getPastTotalSupply(timepoint);
        uint256 reputation =
            reputationRegistry.isActiveAt(account, timepoint) ? reputationRegistry.getPastReputation(account, timepoint) : 0;
        uint256 totalReputation = reputationRegistry.getPastTotalReputation(timepoint);

        return _hybridVotes(tokenVotes, reputation, totalReputation, totalSupply);
    }

    function getPastTotalSupply(uint256 timepoint) public view override returns (uint256) {
        return votesToken.getPastTotalSupply(timepoint);
    }

    function delegates(address account) public view override returns (address) {
        return votesToken.delegates(account);
    }

    function delegate(address) external pure override {
        revert DelegationMustBePerformedOnToken();
    }

    function delegateBySig(
        address delegatee,
        uint256 nonce,
        uint256 expiry,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external override {
        votesToken.delegateBySig(delegatee, nonce, expiry, v, r, s);
    }

    function clock() public view override returns (uint48) {
        return Time.blockNumber();
    }

    function CLOCK_MODE() public pure override returns (string memory) {
        return "mode=blocknumber&from=default";
    }

    function _hybridVotes(
        uint256 tokenVotes,
        uint256 reputation,
        uint256 totalReputation,
        uint256 baseSupply
    ) internal pure returns (uint256) {
        uint256 tokenComponent = Math.mulDiv(tokenVotes, TOKEN_WEIGHT_BPS, WEIGHT_DENOMINATOR);
        if (totalReputation == 0) {
            return tokenComponent;
        }

        uint256 reputationComponent = Math.mulDiv(
            reputation,
            REPUTATION_WEIGHT_BPS * baseSupply,
            totalReputation * WEIGHT_DENOMINATOR
        );
        return tokenComponent + reputationComponent;
    }
}
