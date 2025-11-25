// URL parameter helpers for Exporter Dashboard

/**
 * Get a parameter value from URLSearchParams, returning undefined if null.
 */
export function getParam(sp: URLSearchParams, key: string): string | undefined {
  const v = sp.get(key);
  return v === null ? undefined : v;
}

/**
 * Build a URL with query parameters, omitting undefined values.
 */
export function buildUrl(
  base: string,
  params: Record<string, string | undefined>
): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') {
      usp.set(k, v);
    }
  }
  const qs = usp.toString();
  return qs ? `${base}?${qs}` : base;
}

/**
 * Navigate to a URL with parameters using the provided navigate function.
 */
export function setParams(
  navigate: (to: string, options?: { replace?: boolean }) => void,
  base: string,
  params: Record<string, string | undefined>,
  options?: { replace?: boolean }
): void {
  const url = buildUrl(base, params);
  navigate(url, options ?? { replace: true });
}

