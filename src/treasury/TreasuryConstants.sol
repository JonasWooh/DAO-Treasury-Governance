// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library TreasuryConstants {
    uint256 internal constant BPS_DENOMINATOR = 10_000;
    uint256 internal constant DEFAULT_MIN_LIQUID_RESERVE_BPS = 3_000;
    uint256 internal constant DEFAULT_MAX_SINGLE_GRANT_BPS = 2_000;
    uint256 internal constant DEFAULT_STALE_PRICE_THRESHOLD = 3_600;
    uint8 internal constant WETH_DECIMALS = 18;
    uint8 internal constant USD_DECIMALS = 18;
    uint8 internal constant MAX_POWER_OF_TEN_EXPONENT = 77;
}