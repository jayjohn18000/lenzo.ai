// frontend/lib/safe-formatters.ts
/**
 * Type-safe number formatting utilities with proper error handling
 */

export type FormattableValue = number | string | null | undefined;

/**
 * Safely format a number with toFixed, returns fallback for invalid values
 */
export function safeToFixed(
  value: FormattableValue,
  decimals: number = 2,
  fallback: string = '--'
): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(num) || !isFinite(num)) {
    console.warn(`[safeToFixed] Invalid value: ${value}`);
    return fallback;
  }
  
  try {
    return num.toFixed(decimals);
  } catch (error) {
    console.error('[safeToFixed] Formatting error:', error);
    return fallback;
  }
}

/**
 * Format currency values safely
 */
export function safeCurrency(
  value: FormattableValue,
  decimals: number = 4,
  prefix: string = '$',
  fallback: string = '--'
): string {
  const formatted = safeToFixed(value, decimals, '');
  return formatted ? `${prefix}${formatted}` : fallback;
}

/**
 * Format percentage values safely (assumes 0-1 range)
 */
export function safePercentage(
  value: FormattableValue,
  decimals: number = 1,
  fallback: string = '--'
): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(num) || !isFinite(num)) {
    return fallback;
  }
  
  // Handle both 0-1 and 0-100 ranges
  const percentage = num <= 1 ? num * 100 : num;
  return `${safeToFixed(percentage, decimals, '')}%`;
}

/**
 * Format time values safely (ms to seconds)
 */
export function safeTime(
  valueMs: FormattableValue,
  unit: 'ms' | 's' = 's',
  decimals: number = 1,
  fallback: string = '--'
): string {
  if (valueMs === null || valueMs === undefined) {
    return fallback;
  }
  
  const num = typeof valueMs === 'string' ? parseFloat(valueMs) : valueMs;
  
  if (isNaN(num) || !isFinite(num)) {
    return fallback;
  }
  
  const value = unit === 's' ? num / 1000 : num;
  return `${safeToFixed(value, decimals, '')}${unit}`;
}

/**
 * Type guard to check if value is a valid number
 */
export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

/**
 * Type guard for numeric string
 */
export function isNumericString(value: unknown): value is string {
  return typeof value === 'string' && !isNaN(parseFloat(value)) && isFinite(parseFloat(value));
}

/**
 * Ensure a value is numeric, with optional default
 */
export function ensureNumeric(value: FormattableValue, defaultValue: number = 0): number {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(num) || !isFinite(num)) {
    return defaultValue;
  }
  
  return num;
}