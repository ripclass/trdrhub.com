/**
 * CSRF token management utilities.
 */

const CSRF_STORAGE_KEY = 'csrf_token';
let inFlightCsrfFetch: Promise<string | null> | null = null;

function getStoredCsrfToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(CSRF_STORAGE_KEY);
    return stored && stored.trim().length > 0 ? stored : null;
  } catch {
    return null;
  }
}

function setStoredCsrfToken(token: string | null): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    if (token && token.trim().length > 0) {
      window.localStorage.setItem(CSRF_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(CSRF_STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors; the in-memory request still uses the token.
  }
}

/**
 * Get CSRF token from local cache or cookie.
 */
export function getCsrfToken(): string | null {
  const storedToken = getStoredCsrfToken();
  if (storedToken) {
    return storedToken;
  }

  if (typeof document === 'undefined') {
    return null;
  }

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrf_token') {
      const token = decodeURIComponent(value);
      setStoredCsrfToken(token);
      return token;
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
export async function fetchCsrfToken(
  apiBaseUrl: string,
  options?: { forceRefresh?: boolean },
): Promise<string | null> {
  const forceRefresh = Boolean(options?.forceRefresh);
  if (!forceRefresh) {
    const existing = getCsrfToken();
    if (existing) {
      return existing;
    }
    if (inFlightCsrfFetch) {
      return inFlightCsrfFetch;
    }
  }

  inFlightCsrfFetch = (async () => {
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
        setStoredCsrfToken(null);
        return null;
      }

      const data = await response.json();
      const token = data.csrf_token || null;
      setStoredCsrfToken(token);
      return token;
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
      setStoredCsrfToken(null);
      return null;
    } finally {
      inFlightCsrfFetch = null;
    }
  })();

  return inFlightCsrfFetch;
}

