/**
 * Shared TanStack Query options. `STATIC` marks data that never changes
 * during a session (Pokédex master tables, type chart, etc.) so React Query
 * never refetches it after the first successful load.
 */
export const STATIC = { staleTime: Infinity } as const;
