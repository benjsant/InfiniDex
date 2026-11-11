"use client";

import { useCallback, useMemo, useState, useSyncExternalStore } from "react";
import { readRaw, subscribe, writeRaw } from "@/lib/localStore";

function parse<T>(raw: string | null, fallback: T): T {
  if (raw === null) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/**
 * State persisted to localStorage. Returns `defaultValue` during SSR and
 * hydration (server snapshot), then the stored value. Every instance using the
 * same key stays in sync, across tabs too. Malformed JSON falls back to the
 * default; storage failures keep the value in memory for the session.
 */
export function useLocalStorageState<T>(
  key: string,
  defaultValue: T,
): [T, (updater: T | ((prev: T) => T)) => void] {
  // Figé au premier rendu : les appelants passent souvent un littéral (`[]`).
  const [fallback] = useState(defaultValue);

  // Le snapshot est la chaîne brute : comparée par valeur, donc stable.
  const raw = useSyncExternalStore(
    subscribe,
    () => readRaw(key),
    () => null,
  );
  const state = useMemo(() => parse(raw, fallback), [raw, fallback]);

  const setStored = useCallback(
    (updater: T | ((prev: T) => T)) => {
      // Relu à chaque appel : deux mises à jour successives se composent.
      const prev = parse(readRaw(key), fallback);
      const next =
        typeof updater === "function" ? (updater as (p: T) => T)(prev) : updater;
      writeRaw(key, JSON.stringify(next));
    },
    [key, fallback],
  );

  return [state, setStored];
}
