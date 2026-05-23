"use client";

import { useCallback } from "react";
import { useLocalStorageState } from "@/hooks/useLocalStorageState";

const STORAGE_KEY = "infinidex_history";
const MAX_ENTRIES = 20;

export interface FusionHistoryEntry {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
  visitedAt: number;
}

export function useHistory() {
  const [entries, setEntries] = useLocalStorageState<FusionHistoryEntry[]>(STORAGE_KEY, []);

  const addEntry = useCallback(
    (entry: Omit<FusionHistoryEntry, "visitedAt">) => {
      setEntries((prev) => {
        const filtered = prev.filter(
          (e) => !(e.headId === entry.headId && e.bodyId === entry.bodyId),
        );
        return [{ ...entry, visitedAt: Date.now() }, ...filtered].slice(0, MAX_ENTRIES);
      });
    },
    [setEntries],
  );

  const clearHistory = useCallback(() => setEntries([]), [setEntries]);

  return { entries, addEntry, clearHistory };
}
