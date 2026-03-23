import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('csrf helper', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('prefers a cached localStorage token', async () => {
    localStorage.setItem('csrf_token', 'cached-token');

    const { getCsrfToken } = await import('@/lib/csrf');

    expect(getCsrfToken()).toBe('cached-token');
  });

  it('deduplicates concurrent token fetches and caches the result', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ csrf_token: 'token-a' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { fetchCsrfToken } = await import('@/lib/csrf');

    const [first, second] = await Promise.all([
      fetchCsrfToken('https://api.example.com'),
      fetchCsrfToken('https://api.example.com'),
    ]);

    expect(first).toBe('token-a');
    expect(second).toBe('token-a');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem('csrf_token')).toBe('token-a');
  });

  it('force refresh bypasses the cached token', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ csrf_token: 'token-a' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ csrf_token: 'token-b' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const { fetchCsrfToken } = await import('@/lib/csrf');

    expect(await fetchCsrfToken('https://api.example.com')).toBe('token-a');
    expect(await fetchCsrfToken('https://api.example.com', { forceRefresh: true })).toBe(
      'token-b',
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(localStorage.getItem('csrf_token')).toBe('token-b');
  });
});
