import { useQuery } from "@tanstack/react-query";
import { getFusion, getFusionFull, getFusionMoves, getFusionExpertMoves, getFusionAbilities, getSprites, getFeaturedFusions, getTopFusionsForPokemon } from "@/lib/api";

const STATIC = { staleTime: Infinity } as const;

const enabled = (headId: number | null, bodyId: number | null) =>
  headId != null && bodyId != null && headId > 0 && bodyId > 0;

/** Single round-trip replacing useFusion + useFusionMoves + useFusionExpertMoves. */
export function useFusionFull(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion-full", headId, bodyId],
    queryFn: () => getFusionFull(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useFusion(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion", headId, bodyId],
    queryFn: () => getFusion(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useFusionMoves(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion-moves", headId, bodyId],
    queryFn: () => getFusionMoves(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useFusionExpertMoves(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion-expert-moves", headId, bodyId],
    queryFn: () => getFusionExpertMoves(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useFusionAbilities(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion-abilities", headId, bodyId],
    queryFn: () => getFusionAbilities(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useSprites(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["sprites", headId, bodyId],
    queryFn: () => getSprites(headId!, bodyId!),
    enabled: enabled(headId, bodyId),
    ...STATIC,
  });
}

export function useFeaturedFusions(limit = 50) {
  return useQuery({
    queryKey: ["fusions-featured", limit],
    queryFn: () => getFeaturedFusions(limit),
    staleTime: 5 * 60 * 1000, // refresh every 5 min for variety
  });
}

export function useTopFusionsForPokemon(pokemonId: number | null, limit = 5, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["fusions-top-by-pokemon", pokemonId, limit],
    queryFn: () => getTopFusionsForPokemon(pokemonId!, limit),
    enabled: pokemonId != null && pokemonId > 0,
    ...STATIC,
    ...options,
  });
}
