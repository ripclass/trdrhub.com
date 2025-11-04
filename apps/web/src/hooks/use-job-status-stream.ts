/**
 * React hook for consuming Server-Sent Events (SSE) stream for job status updates.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { BankJob } from "@/api/bank";
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
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) {
      return;
    }

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const streamUrl = `${API_BASE_URL}/bank/jobs/stream`;

      // Get auth token for SSE
      const getAuthToken = async () => {
        try {
          const { supabase } = await import("@/lib/supabase");
          const session = await supabase.auth.getSession();
          return session.data.session?.access_token || null;
        } catch {
          return null;
        }
      };

      // Create EventSource with auth token in URL (if available)
      // Note: EventSource doesn't support custom headers, so we'll use query param or cookie
      // For now, rely on cookie-based auth if available, otherwise use query param
      getAuthToken().then((token) => {
        // Encode token properly for URL
        const url = token ? `${streamUrl}?token=${encodeURIComponent(token)}` : streamUrl;
        
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setIsConnected(true);
          reconnectAttempts.current = 0;
          console.log("SSE connection opened");
        };

        eventSource.onmessage = (event) => {
          try {
            const jobData = JSON.parse(event.data) as BankJob;
            
            // Update jobs state
            setJobs((prevJobs) => {
              const existingIndex = prevJobs.findIndex((j) => j.id === jobData.id);
              
              if (existingIndex >= 0) {
                // Update existing job
                const updated = [...prevJobs];
                updated[existingIndex] = jobData;
                return updated;
              } else {
                // Add new job
                return [...prevJobs, jobData];
              }
            });

            // Call callback if provided
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
          
          // Close and attempt reconnect
          eventSource.close();
          eventSourceRef.current = null;

          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current += 1;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000); // Exponential backoff, max 30s
            
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, delay);
          } else {
            console.error("Max reconnect attempts reached");
            if (onError) {
              onError(new Error("Failed to connect to job status stream"));
            }
          }
        };
      });
    } catch (error) {
      console.error("Failed to create SSE connection:", error);
      if (onError) {
        onError(error as Error);
      }
    }
  }, [enabled, onJobUpdate, onError]);

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
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    jobs,
    isConnected,
    connect,
    disconnect,
  };
}

