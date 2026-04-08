/**
 * useValidationProgress
 *
 * Connects to the validation pipeline SSE stream to receive real-time
 * checkpoint events while a validation POST is in flight. Replaces the
 * fake client-side timer in the upload UI.
 *
 * Flow:
 * 1. Caller generates a UUID v4 (clientRequestId) BEFORE submitting validation
 * 2. Caller calls this hook with that id and `enabled: true`
 * 3. Hook fetches a short-lived stream token, opens an EventSource
 * 4. Hook reports stage/progress/message as events arrive
 * 5. Hook closes the connection on terminal events or when disabled
 *
 * Falls back gracefully when SSE is unavailable (Redis down, network error,
 * unsupported environment) — caller can use the returned `isConnected` flag
 * to decide whether to show fake timer progress instead.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/api/client";

export interface ValidationProgressEvent {
  stage: string;
  progress?: number | null;
  message?: string;
  terminal?: boolean;
  success?: boolean;
  error?: string;
  ts?: number;
}

export interface UseValidationProgressState {
  /** True after the EventSource has opened successfully */
  isConnected: boolean;
  /** Current stage name from the most recent event (e.g. "ocr_extraction_complete") */
  stage: string | null;
  /** Coarse percentage 0-100, may be null until first event with progress */
  progress: number | null;
  /** Human-readable message for the current stage */
  message: string | null;
  /** True after a terminal event with success=true */
  isComplete: boolean;
  /** True after a terminal event with success=false */
  isFailed: boolean;
  /** Most recent error message, if any */
  error: string | null;
}

interface UseValidationProgressOptions {
  /** Client-generated UUID. Must match the X-Client-Request-ID header on the POST. */
  clientRequestId: string | null;
  /** Whether to actually connect. Set false to suspend the stream. */
  enabled: boolean;
}

const INITIAL_STATE: UseValidationProgressState = {
  isConnected: false,
  stage: null,
  progress: null,
  message: null,
  isComplete: false,
  isFailed: false,
  error: null,
};

function resolveApiBase(): string {
  const env = (import.meta as any).env;
  return (env?.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
}

export function useValidationProgress({
  clientRequestId,
  enabled,
}: UseValidationProgressOptions): UseValidationProgressState {
  const [state, setState] = useState<UseValidationProgressState>(INITIAL_STATE);
  const eventSourceRef = useRef<EventSource | null>(null);
  const cancelledRef = useRef(false);

  const closeStream = useCallback(() => {
    if (eventSourceRef.current) {
      try {
        eventSourceRef.current.close();
      } catch {
        // ignore
      }
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled || !clientRequestId) {
      // Reset to initial when disabled
      closeStream();
      setState(INITIAL_STATE);
      return;
    }

    cancelledRef.current = false;

    const connect = async () => {
      try {
        // Step 1: fetch short-lived stream token
        const { data } = await api.get<{ token: string; expires_in: number }>(
          "/api/validate/stream-token",
        );
        if (cancelledRef.current) return;

        // Step 2: open the EventSource
        const apiBase = resolveApiBase();
        const url = `${apiBase}/api/validate/stream/${encodeURIComponent(
          clientRequestId,
        )}?sse_token=${encodeURIComponent(data.token)}`;

        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onopen = () => {
          if (cancelledRef.current) return;
          setState((prev) => ({ ...prev, isConnected: true }));
        };

        es.onmessage = (event) => {
          if (cancelledRef.current) return;
          try {
            const evt = JSON.parse(event.data) as ValidationProgressEvent;

            setState((prev) => ({
              ...prev,
              stage: evt.stage ?? prev.stage,
              progress: evt.progress ?? prev.progress,
              message: evt.message ?? prev.message,
              isComplete: evt.terminal && evt.success === true ? true : prev.isComplete,
              isFailed: evt.terminal && evt.success === false ? true : prev.isFailed,
              error: evt.error ?? prev.error,
            }));

            if (evt.terminal) {
              closeStream();
            }
          } catch (parseErr) {
            // Malformed event — ignore quietly
            console.debug("[useValidationProgress] failed to parse event", parseErr);
          }
        };

        es.onerror = () => {
          // EventSource auto-reconnects unless we close it. For our use case
          // (a single short-lived validation), we want to close on persistent
          // failure rather than reconnect-loop. Mark as not connected.
          if (cancelledRef.current) return;
          setState((prev) => ({ ...prev, isConnected: false }));
          // Close after a brief delay so transient errors don't kill the stream
          setTimeout(() => {
            if (eventSourceRef.current && eventSourceRef.current.readyState === EventSource.CLOSED) {
              closeStream();
            }
          }, 2000);
        };
      } catch (err) {
        if (cancelledRef.current) return;
        const message = err instanceof Error ? err.message : "Failed to connect to progress stream";
        setState((prev) => ({ ...prev, error: message, isConnected: false }));
      }
    };

    void connect();

    return () => {
      cancelledRef.current = true;
      closeStream();
    };
  }, [clientRequestId, enabled, closeStream]);

  return state;
}
