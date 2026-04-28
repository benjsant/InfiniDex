import { useQuery } from "@tanstack/react-query";
import { getFusion } from "@/lib/api";

export function useFusion(headId: number | null, bodyId: number | null) {
  return useQuery({
    queryKey: ["fusion", headId, bodyId],
    queryFn: () => getFusion(headId!, bodyId!),
    enabled: headId != null && bodyId != null && headId > 0 && bodyId > 0,
    staleTime: Infinity,
  });
}
