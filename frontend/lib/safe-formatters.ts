// frontend/lib/safe-formatters.ts
/**
 * Type-safe number formatting utilities with proper error handling.
 * Robust defaults + Intl.NumberFormat support.
 */

export type FormattableValue = number | string | null | undefined;

export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function isNumericString(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const n = Number(value);
  return Number.isFinite(n);
}

export function ensureNumeric(value: FormattableValue, defaultValue = 0): number {
  if (value === null || value === undefined) return defaultValue;
  const n = typeof value === 'string' ? Number(value) : value;
  return Number.isFinite(n as number) ? (n as number) : defaultValue;
}

/* -------------------------------------------------------------------------- */
/*                         Core, predictable number out                       */
/* -------------------------------------------------------------------------- */

export function safeToFixed(
  value: FormattableValue,
  decimals = 2,
  opts?: { trim?: boolean; fallback?: string }
): string {
  const fallback = opts?.fallback ?? '--';
  const trim = opts?.trim ?? false;

  if (value === null || value === undefined) return fallback;
  const n = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(n as number)) return fallback;

  try {
    let out = (n as number).toFixed(decimals);
    if (trim && decimals > 0) {
      // Remove trailing zeros while keeping at least one integer digit
      out = out.replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.$/, '');
    }
    return out;
  } catch {
    return fallback;
  }
}

/* -------------------------------------------------------------------------- */
/*                               Currency format                              */
/* -------------------------------------------------------------------------- */

export type SafeCurrencyOptions = {
  locale?: string;           // e.g., 'en-US'
  currency?: string;         // e.g., 'USD'
  minimumFractionDigits?: number; // default 2
  maximumFractionDigits?: number; // default 4
  fallback?: string;         // default '--'
};

export function safeCurrency(
  value: FormattableValue,
  options: SafeCurrencyOptions = {}
): string {
  const {
    locale,
    currency = 'USD',
    minimumFractionDigits = 2,
    maximumFractionDigits = 4,
    fallback = '--',
  } = options;

  const n = ensureNumeric(value, Number.NaN);
  if (!Number.isFinite(n)) return fallback;

  try {
    const fmt = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits,
      maximumFractionDigits,
    });
    return fmt.format(n);
  } catch {
    // Fallback to plain "$x.y"
    return `$${safeToFixed(n, Math.max(minimumFractionDigits, 0), { fallback })}`;
  }
}

/* -------------------------------------------------------------------------- */
/*                               Percentage format                            */
/* -------------------------------------------------------------------------- */

export type SafePercentageOptions = {
  locale?: string;
  digits?: number;            // number of fraction digits (default 1)
  expectsFraction?: boolean;  // true => input is 0–1. false => input is 0–100.
  fallback?: string;          // default '--'
};

export function safePercentage(
  value: FormattableValue,
  opts: SafePercentageOptions = {}
): string {
  const {
    locale,
    digits = 1,
    expectsFraction = true,
    fallback = '--',
  } = opts;

  const raw = ensureNumeric(value, Number.NaN);
  if (!Number.isFinite(raw)) return fallback;

  const pct = expectsFraction ? raw : raw / 100;

  try {
    const fmt = new Intl.NumberFormat(locale, {
      style: 'percent',
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
    return fmt.format(pct);
  } catch {
    // Fallback: manual formatting
    const as100 = pct * 100;
    return `${safeToFixed(as100, digits, { fallback: '' })}%`;
  }
}

/* -------------------------------------------------------------------------- */
/*                                   Time                                     */
/* -------------------------------------------------------------------------- */

export type SafeTimeOptions = {
  unit?: 'ms' | 's' | 'auto';  // default 's' (we convert ms->s)
  decimals?: number;           // default 1
  fallback?: string;           // default '--'
};

export function safeTime(
  valueMs: FormattableValue,
  options: SafeTimeOptions = {}
): string {
  const { unit = 's', decimals = 1, fallback = '--' } = options;

  const num = ensureNumeric(valueMs, Number.NaN);
  if (!Number.isFinite(num)) return fallback;

  if (unit === 'ms') {
    return `${safeToFixed(num, decimals, { fallback: '' })}ms`;
  }

  if (unit === 'auto') {
    // scale to a friendly unit
    const ms = num;
    if (ms < 1000) return `${safeToFixed(ms, 0, { fallback: '' })}ms`;
    const s = ms / 1000;
    if (s < 60) return `${safeToFixed(s, decimals, { fallback: '' })}s`;
    const m = s / 60;
    if (m < 60) return `${safeToFixed(m, decimals, { fallback: '' })}m`;
    const h = m / 60;
    return `${safeToFixed(h, decimals, { fallback: '' })}h`;
  }

  // default: interpret input as ms, output seconds
  const seconds = num / 1000;
  return `${safeToFixed(seconds, decimals, { fallback: '' })}s`;
}
