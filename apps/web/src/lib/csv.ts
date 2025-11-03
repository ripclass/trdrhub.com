/**
 * Escape CSV value to prevent injection attacks.
 * Wraps values containing commas, quotes, or newlines in quotes
 * and escapes internal quotes.
 */
export function escapeCSV(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '';
  
  const str = String(value);
  
  // If contains comma, quote, or newline, wrap in quotes and escape quotes
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  
  return str;
}

/**
 * Generate CSV content from rows of data.
 * Each row is an array of values that will be escaped.
 */
export function generateCSV(rows: (string | number | null)[][]): string {
  return rows.map(row => row.map(escapeCSV).join(',')).join('\n');
}

