"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * State persisted to localStorage. Hydrates client-side on mount (returns
 * `defaultValue` during SSR / first render to avoid hydration mismatch).
 * Writes and reads are best-effort: SSR, private-browsing quota, or malformed
 * JSON are swallowed and the default is kept.
 */
export function useLocalStorageState<T>(
  key: string,
  defaultValue: T,
): [T, (updater: T | ((prev: T) => T)) => void] {
  const [state, setState] = useState<T>(defaultValue);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw !== null) setState(JSON.parse(raw) as T);
    } catch {
      // keep default
    }
  }, [key]);

  const setStored = useCallback(
    (updater: T | ((prev: T) => T)) => {
      setState((prev) => {
        const next =
          typeof updater === "function" ? (updater as (p: T) => T)(prev) : updater;
        try {
          localStorage.setItem(key, JSON.stringify(next));
        } catch {
          // SSR or quota
        }
        return next;
      });
    },
    [key],
  );

  return [state, setStored];
}
