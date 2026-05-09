"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fusiondex_comparison";

export interface ComparisonSlot {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
}

function readStorage(): [ComparisonSlot | null, ComparisonSlot | null] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [null, null];
  } catch {
    return [null, null];
  }
}

function writeStorage(slots: [ComparisonSlot | null, ComparisonSlot | null]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(slots));
  } catch {}
}

export function useComparison() {
  const [slots, setSlots] = useState<[ComparisonSlot | null, ComparisonSlot | null]>([null, null]);

  useEffect(() => {
    setSlots(readStorage());
  }, []);

  const isInComparison = useCallback(
    (headId: number, bodyId: number) =>
      slots.some((s) => s?.headId === headId && s?.bodyId === bodyId),
    [slots],
  );

  // Add a fusion to the next available slot (slot 0 then slot 1).
  // If both slots are filled, replaces slot 1 and shifts slot 1 → slot 0.
  const addToComparison = useCallback((entry: ComparisonSlot) => {
    setSlots((prev) => {
      // Already present — no-op
      if (prev.some((s) => s?.headId === entry.headId && s?.bodyId === entry.bodyId)) return prev;
      let next: [ComparisonSlot | null, ComparisonSlot | null];
      if (!prev[0]) next = [entry, prev[1]];
      else if (!prev[1]) next = [prev[0], entry];
      else next = [prev[1], entry]; // shift: oldest out, newest in slot 1
      writeStorage(next);
      return next;
    });
  }, []);

  const removeFromComparison = useCallback((headId: number, bodyId: number) => {
    setSlots((prev) => {
      const next: [ComparisonSlot | null, ComparisonSlot | null] = [
        prev[0]?.headId === headId && prev[0]?.bodyId === bodyId ? null : prev[0],
        prev[1]?.headId === headId && prev[1]?.bodyId === bodyId ? null : prev[1],
      ];
      writeStorage(next);
      return next;
    });
  }, []);

  const clearComparison = useCallback(() => {
    writeStorage([null, null]);
    setSlots([null, null]);
  }, []);

  const canCompare = slots[0] !== null && slots[1] !== null;

  return { slots, isInComparison, addToComparison, removeFromComparison, clearComparison, canCompare };
}
