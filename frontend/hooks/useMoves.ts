import { useQuery } from "@tanstack/react-query";
import { getMoves, getMove, searchMoves, getMovesByType } from "@/lib/api";
import { STATIC } from "@/hooks/_queryOptions";

export function useMoves() {
  return useQuery({
    queryKey: ["moves"],
    queryFn: getMoves,
    ...STATIC,
  });
}

export function useMove(id: number) {
  return useQuery({
    queryKey: ["move", id],
    queryFn: () => getMove(id),
    enabled: id > 0,
    ...STATIC,
  });
}

export function useMoveSearch(q: string) {
  return useQuery({
    queryKey: ["move-search", q],
    queryFn: () => searchMoves(q),
    enabled: q.trim().length >= 2,
    ...STATIC,
  });
}

export function useMovesByType(typeName: string) {
  return useQuery({
    queryKey: ["moves-by-type", typeName],
    queryFn: () => getMovesByType(typeName),
    enabled: typeName.length > 0,
    ...STATIC,
  });
}
