"use client";

import { useCallback } from "react";
import { useLocalStorageState } from "@/hooks/useLocalStorageState";

const STORAGE_KEY = "fusiondex_pokemon_favorites";

export interface PokemonFavorite {
  id: number;
  nationalId: number | null;
  nameEn: string;
  nameFr: string | null;
  savedAt: number;
}

export function usePokemonFavorites() {
  const [favorites, setFavorites] = useLocalStorageState<PokemonFavorite[]>(STORAGE_KEY, []);

  const isFavorite = useCallback(
    (id: number) => favorites.some((f) => f.id === id),
    [favorites],
  );

  const toggleFavorite = useCallback(
    (entry: Omit<PokemonFavorite, "savedAt">) => {
      setFavorites((prev) => {
        const exists = prev.some((f) => f.id === entry.id);
        return exists
          ? prev.filter((f) => f.id !== entry.id)
          : [{ ...entry, savedAt: Date.now() }, ...prev];
      });
    },
    [setFavorites],
  );

  const clearFavorites = useCallback(() => setFavorites([]), [setFavorites]);

  return { favorites, isFavorite, toggleFavorite, clearFavorites };
}
