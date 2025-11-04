/**
 * CSRF token management utilities.
 */

/**
 * Get CSRF token from cookie.
 */
export function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrf_token') {
      return decodeURIComponent(value);
    }
  }
  return null;
}

/**
 * Check if an HTTP method requires CSRF protection.
 */
export function requiresCsrfToken(method: string): boolean {
  return ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase());
}

/**
 * Fetch a new CSRF token from the API.
 */
export async function fetchCsrfToken(apiBaseUrl: string): Promise<string | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/auth/csrf-token`, {
      method: 'GET',
      credentials: 'include', // Include cookies
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.warn('Failed to fetch CSRF token:', response.status);
      return null;
    }

    const data = await response.json();
    return data.csrf_token || null;
  } catch (error) {
    console.error('Error fetching CSRF token:', error);
    return null;
  }
}

