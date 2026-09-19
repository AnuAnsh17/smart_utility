/**
 * Rendering helpers for values the backend may legitimately refuse to supply.
 *
 * A missing field stays missing all the way to the screen: it renders as a
 * dash so the reader can tell "the bill did not state this" apart from "this
 * bill said zero".
 */

const DASH = '—';

export function orDash(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return DASH;
  if (typeof value === 'string' && value.trim() === '') return DASH;
  return String(value);
}

export function formatAmount(
  symbol: string,
  amount: number | null | undefined
): string {
  if (amount === null || amount === undefined || !Number.isFinite(amount)) {
    return DASH;
  }
  return `${symbol}${amount.toLocaleString('en-IN')}`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return DASH;
  }
  return value.toLocaleString('en-IN');
}
