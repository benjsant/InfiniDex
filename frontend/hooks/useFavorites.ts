"use client";

import { useCallback } from "react";
import { useLocalStorageState } from "@/hooks/useLocalStorageState";

const STORAGE_KEY = "infinidex_favorites";

export interface FusionFavorite {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
  savedAt: number;
}

export function useFavorites() {
  const [favorites, setFavorites] = useLocalStorageState<FusionFavorite[]>(STORAGE_KEY, []);

  const isFavorite = useCallback(
    (headId: number, bodyId: number) =>
      favorites.some((f) => f.headId === headId && f.bodyId === bodyId),
    [favorites],
  );

  const toggleFavorite = useCallback(
    (entry: Omit<FusionFavorite, "savedAt">) => {
      setFavorites((prev) => {
        const exists = prev.some(
          (f) => f.headId === entry.headId && f.bodyId === entry.bodyId,
        );
        return exists
          ? prev.filter((f) => !(f.headId === entry.headId && f.bodyId === entry.bodyId))
          : [{ ...entry, savedAt: Date.now() }, ...prev];
      });
    },
    [setFavorites],
  );

  const clearFavorites = useCallback(() => setFavorites([]), [setFavorites]);

  return { favorites, isFavorite, toggleFavorite, clearFavorites };
}
