"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fusiondex_pokemon_favorites";

export interface PokemonFavorite {
  id: number;
  nationalId: number | null;
  nameEn: string;
  nameFr: string | null;
  savedAt: number;
}

function readStorage(): PokemonFavorite[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PokemonFavorite[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(entries: PokemonFavorite[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {}
}

export function usePokemonFavorites() {
  const [favorites, setFavorites] = useState<PokemonFavorite[]>([]);

  useEffect(() => {
    setFavorites(readStorage());
  }, []);

  const isFavorite = useCallback(
    (id: number) => favorites.some((f) => f.id === id),
    [favorites],
  );

  const toggleFavorite = useCallback(
    (entry: Omit<PokemonFavorite, "savedAt">) => {
      setFavorites((prev) => {
        const exists = prev.some((f) => f.id === entry.id);
        const next = exists
          ? prev.filter((f) => f.id !== entry.id)
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
