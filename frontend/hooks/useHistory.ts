"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fusiondex_history";
const MAX_ENTRIES = 20;

export interface FusionHistoryEntry {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
  visitedAt: number;
}

function readStorage(): FusionHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as FusionHistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(entries: FusionHistoryEntry[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // localStorage unavailable (SSR, private browsing quota exceeded)
  }
}

export function useHistory() {
  const [entries, setEntries] = useState<FusionHistoryEntry[]>([]);

  // Hydrate from localStorage on mount (client only)
  useEffect(() => {
    setEntries(readStorage());
  }, []);

  const addEntry = useCallback((entry: Omit<FusionHistoryEntry, "visitedAt">) => {
    setEntries((prev) => {
      // Move to top if already present, otherwise prepend
      const filtered = prev.filter(
        (e) => !(e.headId === entry.headId && e.bodyId === entry.bodyId),
      );
      const next = [{ ...entry, visitedAt: Date.now() }, ...filtered].slice(0, MAX_ENTRIES);
      writeStorage(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    writeStorage([]);
    setEntries([]);
  }, []);

  return { entries, addEntry, clearHistory };
}
