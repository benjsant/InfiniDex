"use client";

import { useCallback } from "react";
import { useLocalStorageState } from "@/hooks/useLocalStorageState";

const STORAGE_KEY = "fusiondex_comparison";

export interface ComparisonSlot {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
}

type Slots = [ComparisonSlot | null, ComparisonSlot | null];

export function useComparison() {
  const [slots, setSlots] = useLocalStorageState<Slots>(STORAGE_KEY, [null, null]);

  const isInComparison = useCallback(
    (headId: number, bodyId: number) =>
      slots.some((s) => s?.headId === headId && s?.bodyId === bodyId),
    [slots],
  );

  // Add a fusion to the next available slot (slot 0 then slot 1).
  // If both slots are filled, replaces slot 1 and shifts slot 1 → slot 0.
  const addToComparison = useCallback(
    (entry: ComparisonSlot) => {
      setSlots((prev) => {
        if (prev.some((s) => s?.headId === entry.headId && s?.bodyId === entry.bodyId)) return prev;
        if (!prev[0]) return [entry, prev[1]];
        if (!prev[1]) return [prev[0], entry];
        return [prev[1], entry];
      });
    },
    [setSlots],
  );

  const removeFromComparison = useCallback(
    (headId: number, bodyId: number) => {
      setSlots((prev) => [
        prev[0]?.headId === headId && prev[0]?.bodyId === bodyId ? null : prev[0],
        prev[1]?.headId === headId && prev[1]?.bodyId === bodyId ? null : prev[1],
      ]);
    },
    [setSlots],
  );

  const clearComparison = useCallback(() => setSlots([null, null]), [setSlots]);

  const canCompare = slots[0] !== null && slots[1] !== null;

  return { slots, isInComparison, addToComparison, removeFromComparison, clearComparison, canCompare };
}
