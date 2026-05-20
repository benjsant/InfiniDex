import { useQuery } from "@tanstack/react-query";
import { getItems, searchItems } from "@/lib/api";
import { STATIC } from "@/hooks/_queryOptions";

export function useItems(category?: string) {
  return useQuery({
    queryKey: ["items", category ?? "all"],
    queryFn: () => getItems(category),
    ...STATIC,
  });
}

export function useItemSearch(q: string) {
  return useQuery({
    queryKey: ["item-search", q],
    queryFn: () => searchItems(q),
    enabled: q.trim().length >= 2,
    ...STATIC,
  });
}
