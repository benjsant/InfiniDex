import { useQuery } from "@tanstack/react-query";
import {
  getPokemon,
  getPokemonList,
  getPokemonMoves,
  getPokemonEvolutions,
  getPokemonWeaknesses,
  getTypes,
  searchPokemon,
} from "@/lib/api";

// Pokémon data is static between deploys — never refetch in background.
const STATIC: { staleTime: number } = { staleTime: Infinity };

export function usePokemonList(
  params?: { type_id?: number; gen?: number; page?: number; page_size?: number },
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["pokemon-list", params],
    queryFn: () => getPokemonList(params),
    ...STATIC,
    ...options,
  });
}

export function useTypes() {
  return useQuery({
    queryKey: ["types"],
    queryFn: () => getTypes(),
    ...STATIC,
  });
}

export function usePokemonSearch(q: string) {
  return useQuery({
    queryKey: ["pokemon-search", q],
    queryFn: () => searchPokemon(q),
    enabled: q.trim().length >= 2,
    ...STATIC,
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

export function usePokemonMoves(id: number) {
  return useQuery({
    queryKey: ["pokemon-moves", id],
    queryFn: () => getPokemonMoves(id),
    enabled: id > 0,
    ...STATIC,
  });
}

export function usePokemonEvolutions(id: number) {
  return useQuery({
    queryKey: ["pokemon-evolutions", id],
    queryFn: () => getPokemonEvolutions(id),
    enabled: id > 0,
    ...STATIC,
  });
}

export function usePokemonWeaknesses(id: number) {
  return useQuery({
    queryKey: ["pokemon-weaknesses", id],
    queryFn: () => getPokemonWeaknesses(id),
    enabled: id > 0,
    ...STATIC,
  });
}
