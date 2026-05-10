import { useQuery } from "@tanstack/react-query";
import { getFusion, getFusionMoves, getFusionExpertMoves, getFusionAbilities, getSprites } from "@/lib/api";

const STATIC = { staleTime: Infinity } as const;

const enabled = (headId: number | null, bodyId: number | null) =>
  headId != null && bodyId != null && headId > 0 && bodyId > 0;

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
