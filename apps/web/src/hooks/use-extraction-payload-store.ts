import { useCallback, useState } from "react";

const STORAGE_KEY = "lcopilot_extraction_payload";

export function useExtractionPayloadStore<T = unknown>(): [
  T | null,
  (value: T | null) => void,
] {
  const [payload, setRaw] = useState<T | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      return stored ? (JSON.parse(stored) as T) : null;
    } catch {
      return null;
    }
  });

  const set = useCallback((value: T | null) => {
    setRaw(value);
    try {
      if (value) {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      } else {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      /* storage full or unavailable — non-critical */
    }
  }, []);

  return [payload, set];
}
