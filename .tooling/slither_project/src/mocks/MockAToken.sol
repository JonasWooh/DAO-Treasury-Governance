// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockAToken is ERC20 {
    error InvalidPool(address pool);
    error UnauthorizedCaller(address caller);

    address public immutable pool;

    constructor(address pool_) ERC20("Mock Aave Wrapped Ether", "maWETH") {
        if (pool_ == address(0)) {
            revert InvalidPool(address(0));
        }

        pool = pool_;
    }

    function mint(address to, uint256 amount) external {
        if (msg.sender != pool) {
            revert UnauthorizedCaller(msg.sender);
        }

        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        if (msg.sender != pool) {
            revert UnauthorizedCaller(msg.sender);
        }

        _burn(from, amount);
    }
}