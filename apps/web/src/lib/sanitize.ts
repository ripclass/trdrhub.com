/**
 * Sanitize text input to prevent XSS attacks.
 * Removes all HTML tags and returns plain text.
 * 
 * Uses regex-based sanitization that works in all environments.
 * Note: For enhanced XSS protection, DOMPurify can be added later if needed.
 */
export function sanitizeText(input: string): string {
  if (!input || typeof input !== 'string') {
    return '';
  }

  // Remove HTML tags and trim whitespace
  return input.replace(/<[^>]*>/g, '').trim();
}

/**
 * Sanitize display text while guaranteeing a non-empty fallback.
 */
export function sanitizeDisplayText(input: string | undefined | null, fallback: string): string {
  if (!input || typeof input !== 'string') {
    return fallback;
  }

  const sanitized = sanitizeText(input);
  return sanitized || fallback;
}

/**
 * Sanitize file name to prevent path traversal and other attacks.
 * Removes path separators and dangerous characters, limits length.
 */
export function sanitizeFileName(fileName: string): string {
  if (!fileName || typeof fileName !== 'string') {
    return '';
  }
  
  // Remove path separators and dangerous characters
  return fileName.replace(/[\/\\<>:"|?*]/g, '').slice(0, 255);
}

