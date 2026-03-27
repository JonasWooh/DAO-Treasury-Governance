// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Votes} from "@openzeppelin/contracts/governance/utils/Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";

import {ICampusInnovationFundToken} from "../interfaces/ICampusInnovationFundToken.sol";
import {GovernanceConstants} from "./GovernanceConstants.sol";

contract CampusInnovationFundToken is ICampusInnovationFundToken, ERC20, ERC20Permit, ERC20Votes, Ownable {
    error MaxSupplyExceeded(uint256 requestedTotalSupply, uint256 maxSupply);

    constructor(address initialOwner)
        ERC20(GovernanceConstants.TOKEN_NAME, GovernanceConstants.TOKEN_SYMBOL)
        ERC20Permit(GovernanceConstants.TOKEN_NAME)
        Ownable(initialOwner)
    {}

    function mint(address to, uint256 amount) external override onlyOwner {
        uint256 nextSupply = totalSupply() + amount;
        uint256 supplyCap = maxSupply();
        if (nextSupply > supplyCap) {
            revert MaxSupplyExceeded(nextSupply, supplyCap);
        }

        _mint(to, amount);
    }

    function delegate(address delegatee) public override(ICampusInnovationFundToken, Votes) {
        super.delegate(delegatee);
    }

    function getVotes(address account) public view override(ICampusInnovationFundToken, Votes) returns (uint256) {
        return super.getVotes(account);
    }

    function getPastVotes(
        address account,
        uint256 timepoint
    ) public view override(ICampusInnovationFundToken, Votes) returns (uint256) {
        return super.getPastVotes(account, timepoint);
    }

    function getPastTotalSupply(
        uint256 timepoint
    ) public view override(ICampusInnovationFundToken, Votes) returns (uint256) {
        return super.getPastTotalSupply(timepoint);
    }

    function maxSupply() public pure override returns (uint256) {
        return GovernanceConstants.CIF_TOTAL_SUPPLY;
    }

    function remainingSupply() external view override returns (uint256) {
        return maxSupply() - totalSupply();
    }

    function _maxSupply() internal pure override returns (uint256) {
        return GovernanceConstants.CIF_TOTAL_SUPPLY;
    }

    function _update(address from, address to, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._update(from, to, amount);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}