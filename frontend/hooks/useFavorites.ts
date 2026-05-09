"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fusiondex_favorites";

export interface FusionFavorite {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
  savedAt: number;
}

function readStorage(): FusionFavorite[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as FusionFavorite[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(entries: FusionFavorite[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {}
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<FusionFavorite[]>([]);

  useEffect(() => {
    setFavorites(readStorage());
  }, []);

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
        const next = exists
          ? prev.filter((f) => !(f.headId === entry.headId && f.bodyId === entry.bodyId))
          : [{ ...entry, savedAt: Date.now() }, ...prev];
        writeStorage(next);
        return next;
      });
    },
    [],
  );

  const clearFavorites = useCallback(() => {
    writeStorage([]);
    setFavorites([]);
  }, []);

  return { favorites, isFavorite, toggleFavorite, clearFavorites };
}
