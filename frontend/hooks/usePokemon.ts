import { useQuery } from "@tanstack/react-query";
import {
  getPokemon,
  getPokemonList,
  getPokemonCount,
  getPokemonMoves,
  getPokemonEvolutions,
  getPokemonWeaknesses,
  getTypes,
  getGenerations,
  searchPokemon,
} from "@/lib/api";

// Pokémon data is static between deploys — never refetch in background.
const STATIC: { staleTime: number } = { staleTime: Infinity };

export function usePokemonList(
  params?: {
    type_id?: number;
    gen?: number;
    page?: number;
    page_size?: number;
    include_hoenn?: boolean;
    min_bst?: number;
    max_bst?: number;
    sort_by?: "id" | "bst_asc" | "bst_desc";
  },
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["pokemon-list", params],
    queryFn: () => getPokemonList(params),
    ...STATIC,
    ...options,
  });
}

export function usePokemonCount(
  params?: {
    type_id?: number;
    gen?: number;
    include_hoenn?: boolean;
    min_bst?: number;
    max_bst?: number;
  },
) {
  return useQuery({
    queryKey: ["pokemon-count", params],
    queryFn: () => getPokemonCount(params),
    ...STATIC,
  });
}

export function useTypes() {
  return useQuery({
    queryKey: ["types"],
    queryFn: () => getTypes(),
    ...STATIC,
  });
}

export function useGenerations() {
  return useQuery({
    queryKey: ["generations"],
    queryFn: () => getGenerations(),
    ...STATIC,
  });
}

export function usePokemonSearch(q: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["pokemon-search", q],
    queryFn: () => searchPokemon(q),
    enabled: q.trim().length >= 2,
    ...STATIC,
    ...options,
  });
}

export function usePokemon(id: number) {
  return useQuery({
    queryKey: ["pokemon", id],
    queryFn: () => getPokemon(id),
    enabled: id > 0,
    ...STATIC,
  });
}

export function usePokemonMoves(id: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["pokemon-moves", id],
    queryFn: () => getPokemonMoves(id),
    enabled: id > 0,
    ...STATIC,
    ...options,
  });
}

export function usePokemonEvolutions(id: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["pokemon-evolutions", id],
    queryFn: () => getPokemonEvolutions(id),
    enabled: id > 0,
    ...STATIC,
    ...options,
  });
}

export function usePokemonWeaknesses(id: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["pokemon-weaknesses", id],
    queryFn: () => getPokemonWeaknesses(id),
    enabled: id > 0,
    ...STATIC,
    ...options,
  });
}
