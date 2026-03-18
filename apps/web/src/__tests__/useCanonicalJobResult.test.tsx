import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCanonicalJobResult } from '@/hooks/use-lcopilot';
import { api } from '@/api/client';
import { buildValidationResults } from './fixtures/lcopilot';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/config/featureFlagService', () => ({
  isLCopilotFeatureEnabled: vi.fn(() => false),
}));

const mockedApiGet = vi.mocked(api.get);

const buildWrapper = (queryClient: QueryClient) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };

describe('useCanonicalJobResult', () => {
  beforeEach(() => {
    mockedApiGet.mockReset();
  });

  it('loads canonical results for direct job route entry', async () => {
    const payload = buildValidationResults({ jobId: 'job-1' });
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-1') {
        return { data: { jobId: 'job-1', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-1') {
        return { data: payload } as any;
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const { result } = renderHook(() => useCanonicalJobResult('job-1'), {
      wrapper: buildWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.results?.jobId).toBe('job-1'));
    expect(mockedApiGet).toHaveBeenCalledWith('/api/results/job-1');
  });

  it('normalizes a live wrapped results payload instead of falling into terminal no-results state', async () => {
    const payload = buildValidationResults({ jobId: 'job-live' });
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-live') {
        return { data: { jobId: 'job-live', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-live') {
        return {
          data: {
            job_id: 'job-live',
            jobId: 'job-live',
            structured_result: payload.structured_result,
            telemetry: { UnifiedStructuredResultServed: true },
          },
        } as any;
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const { result } = renderHook(() => useCanonicalJobResult('job-live'), {
      wrapper: buildWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.results?.jobId).toBe('job-live'));
    expect(result.current.results?.structured_result?.version).toBe('structured_result_v1');
    expect(result.current.resultsError).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('clears stale results immediately when the route switches to a different job', async () => {
    const firstPayload = buildValidationResults({ jobId: 'job-1' });
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-1') {
        return { data: { jobId: 'job-1', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-1') {
        return { data: firstPayload } as any;
      }
      if (url === '/api/jobs/job-2') {
        return { data: { jobId: 'job-2', status: 'processing' } } as any;
      }
      if (url === '/api/results/job-2') {
        throw { response: { status: 404, data: { detail: 'not ready' } } };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const { result, rerender } = renderHook(({ jobId }) => useCanonicalJobResult(jobId), {
      initialProps: { jobId: 'job-1' as string | null },
      wrapper: buildWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.results?.jobId).toBe('job-1'));

    act(() => {
      rerender({ jobId: 'job-2' });
    });

    expect(result.current.results).toBeNull();
  });

  it('reuses cached canonical results when reopening the same job in-session', async () => {
    const payload = buildValidationResults({ jobId: 'job-cache' });
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-cache') {
        return { data: { jobId: 'job-cache', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-cache') {
        return { data: payload } as any;
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const wrapper = buildWrapper(queryClient);
    const first = renderHook(() => useCanonicalJobResult('job-cache'), { wrapper });

    await waitFor(() => expect(first.result.current.results?.jobId).toBe('job-cache'));
    act(() => {
      first.unmount();
    });

    const second = renderHook(() => useCanonicalJobResult('job-cache'), { wrapper });

    expect(second.result.current.results?.jobId).toBe('job-cache');
  });

  it('stops reporting loading when a terminal job cannot load results after timeout', async () => {
    vi.useFakeTimers();
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-timeout') {
        return { data: { jobId: 'job-timeout', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-timeout') {
        throw { response: { status: 404, data: { detail: 'not ready' } } };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const { result } = renderHook(() => useCanonicalJobResult('job-timeout'), {
      wrapper: buildWrapper(queryClient),
    });

    await waitFor(() => expect(mockedApiGet).toHaveBeenCalledWith('/api/results/job-timeout'));

    await act(async () => {
      vi.advanceTimersByTime(4500);
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.results).toBeNull();

    vi.useRealTimers();
  });

  it('retries auth-hydration failures before surfacing terminal results errors', async () => {
    vi.useFakeTimers();
    let resultsAttempts = 0;
    mockedApiGet.mockImplementation(async (url: string) => {
      if (url === '/api/jobs/job-auth-race') {
        return { data: { jobId: 'job-auth-race', status: 'completed' } } as any;
      }
      if (url === '/api/results/job-auth-race') {
        resultsAttempts += 1;
        if (resultsAttempts < 3) {
          throw { response: { status: 403, data: { detail: 'Not authenticated' } } };
        }
        return { data: buildValidationResults({ jobId: 'job-auth-race' }) } as any;
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const queryClient = new QueryClient();
    const { result } = renderHook(() => useCanonicalJobResult('job-auth-race'), {
      wrapper: buildWrapper(queryClient),
    });

    await waitFor(() => expect(resultsAttempts).toBe(1));

    await act(async () => {
      vi.advanceTimersByTime(1300);
    });
    await waitFor(() => expect(resultsAttempts).toBe(2));

    await act(async () => {
      vi.advanceTimersByTime(1300);
    });
    await waitFor(() => expect(result.current.results?.jobId).toBe('job-auth-race'));
    expect(result.current.resultsError).toBeNull();

    vi.useRealTimers();
  });
});
