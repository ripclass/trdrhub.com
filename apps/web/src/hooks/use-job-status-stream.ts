/**
 * React hook for consuming Server-Sent Events (SSE) stream for job status updates.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { BankJob, BankJobsResponse } from "@/api/bank";
import { api } from "@/api/client";

interface UseJobStatusStreamOptions {
  enabled?: boolean;
  onJobUpdate?: (job: BankJob) => void;
  onError?: (error: Error) => void;
}

export function useJobStatusStream({
  enabled = true,
  onJobUpdate,
  onError,
}: UseJobStatusStreamOptions = {}) {
  const [jobs, setJobs] = useState<BankJob[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [streamToken, setStreamToken] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const loadInitialJobs = useCallback(async () => {
    try {
      const { data } = await api.get<BankJobsResponse>("/bank/jobs");
      setJobs(data.jobs || []);
    } catch (error) {
      console.error("Failed to load initial jobs:", error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [onError]);

  const fetchStreamToken = useCallback(async () => {
    if (!enabled) {
      return;
    }

    try {
      const { data } = await api.get<{ token: string; expires_in: number }>("/bank/jobs/stream-token");
      setStreamToken(data.token);
      reconnectAttempts.current = 0;
      await loadInitialJobs();
    } catch (error) {
      console.error("Failed to fetch stream token:", error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [enabled, onError, loadInitialJobs]);

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current || !streamToken) {
      return;
    }

    try {
      const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
      const streamUrl = `${API_BASE_URL}/bank/jobs/stream?sse_token=${encodeURIComponent(streamToken)}`;

      const eventSource = new EventSource(streamUrl, { withCredentials: true });
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const jobData = JSON.parse(event.data) as BankJob;

          if (!jobData || !jobData.id) {
            return;
          }

          setJobs((prevJobs) => {
            const existingIndex = prevJobs.findIndex((j) => j.id === jobData.id);

            if (existingIndex >= 0) {
              const updated = [...prevJobs];
              updated[existingIndex] = jobData;
              return updated;
            }

            return [...prevJobs, jobData];
          });

          if (onJobUpdate) {
            onJobUpdate(jobData);
          }
        } catch (error) {
          console.error("Failed to parse SSE event data:", error);
          if (onError) {
            onError(error as Error);
          }
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE connection error:", error);
        setIsConnected(false);

        eventSource.close();
        eventSourceRef.current = null;

        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);

          reconnectTimeoutRef.current = setTimeout(async () => {
            reconnectTimeoutRef.current = null;
            await fetchStreamToken();
          }, delay);
        } else if (onError) {
          onError(new Error("Failed to connect to job status stream"));
        }
      };
    } catch (error) {
      console.error("Failed to create SSE connection:", error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [enabled, streamToken, onJobUpdate, onError, fetchStreamToken]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (enabled) {
      fetchStreamToken();
    } else {
      disconnect();
      setStreamToken(null);
      setJobs([]);
    }

    return () => {
      disconnect();
    };
  }, [enabled, fetchStreamToken, disconnect]);

  useEffect(() => {
    if (enabled && streamToken) {
      connect();
    }
  }, [enabled, streamToken, connect]);

  return {
    jobs,
    isConnected,
    connect,
    disconnect,
  };
}

