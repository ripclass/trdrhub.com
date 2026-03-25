import { beforeEach, describe, expect, it, vi } from 'vitest';

const { getSessionMock } = vi.hoisted(() => ({
  getSessionMock: vi.fn(),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: getSessionMock,
    },
  },
}));

vi.mock('@/lib/csrf', () => ({
  getCsrfToken: vi.fn(() => null),
  requiresCsrfToken: vi.fn(() => false),
}));

describe('api client auth token resolution', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('uses a fresh Supabase token from localStorage without waiting on getSession', async () => {
    localStorage.setItem(
      'sb-live-project-auth-token',
      JSON.stringify({
        access_token: 'local-token',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
      }),
    );
    getSessionMock.mockImplementation(() => new Promise(() => {}));

    const client = await import('@/api/client');

    await expect(client.__internal.getSupabaseAccessToken()).resolves.toBe('local-token');
    expect(getSessionMock).not.toHaveBeenCalled();
  });

  it('falls back to Supabase getSession when no stored token is present', async () => {
    getSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'session-token',
        },
      },
      error: null,
    });

    const client = await import('@/api/client');

    await expect(client.__internal.getSupabaseAccessToken()).resolves.toBe('session-token');
    expect(getSessionMock).toHaveBeenCalledTimes(1);
  });

  it('uses the hardened production API fallback for trdrhub hosts', async () => {
    const client = await import('@/api/client');

    expect(
      client.__internal.resolveApiBaseUrl({
        hostname: 'trdrhub.com',
        protocol: 'https:',
      }),
    ).toBe('https://api.trdrhub.com');
  });
});
