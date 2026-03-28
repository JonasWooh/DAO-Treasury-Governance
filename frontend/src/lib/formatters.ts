export function formatAddress(address: string): string {
  if (address.length < 10) {
    return address;
  }
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function formatCompactIdentifier(value: string, leading = 10, trailing = 8): string {
  if (value.length <= leading + trailing + 3) {
    return value;
  }
  return `${value.slice(0, leading)}...${value.slice(-trailing)}`;
}

export function formatTokenAmount(rawValue: string | bigint, decimals = 18, precision = 4): string {
  const value = typeof rawValue === 'bigint' ? rawValue : BigInt(rawValue);
  const divisor = 10n ** BigInt(decimals);
  const whole = value / divisor;
  const fraction = value % divisor;
  const paddedFraction = fraction.toString().padStart(decimals, '0').slice(0, precision);
  const trimmedFraction = paddedFraction.replace(/0+$/, '');
  return trimmedFraction.length > 0 ? `${whole.toString()}.${trimmedFraction}` : whole.toString();
}

export function formatUsd18(rawValue: string | bigint): string {
  return `$${formatTokenAmount(rawValue, 18, 2)}`;
}

export function formatDateTime(value: number | string): string {
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return 'Unavailable';
  }
  return new Date(numeric * 1000).toLocaleString();
}

export function toEtherscanTxLink(baseUrl: string, txHash: string): string {
  return `${baseUrl}/tx/${txHash}`;
}

export function toEtherscanAddressLink(baseUrl: string, address: string): string {
  return `${baseUrl}/address/${address}`;
}
