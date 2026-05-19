"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Palette, Search } from "lucide-react";
import { listCreators } from "@/lib/api";
import { CreatorModal } from "@/components/fusion/CreatorModal";
import type { CreatorOut } from "@/types/api";

const PAGE_SIZE = 48;

export default function CreatorsPage() {
  const [q, setQ]                               = useState("");
  const [debouncedQ, setDebouncedQ]             = useState("");
  const [page, setPage]                         = useState(1);
  const [selected, setSelected]                 = useState<CreatorOut | null>(null);

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedQ(q); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const offset = (page - 1) * PAGE_SIZE;

  const { data: creators = [], isLoading, isFetching, isError } = useQuery({
    queryKey: ["creators-list", debouncedQ, offset],
    queryFn: () => listCreators(debouncedQ, PAGE_SIZE, offset),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
  });

  // Total count heuristic: if we got a full page, there are more
  const hasMore = creators.length === PAGE_SIZE;
  const hasPrev = page > 1;

  const handleKey = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") setSelected(null);
  }, []);
  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-if-text flex items-center gap-2">
          <Palette size={22} className="text-indigo-400" />
          Galerie des créateurs
        </h1>
        <p className="text-sm text-if-muted mt-1">
          7 081 artistes ont contribué des sprites custom pour Pokémon Infinite Fusion.
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-5 max-w-sm">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-if-muted pointer-events-none" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Rechercher un créateur…"
          className="w-full pl-9 pr-3 py-2 rounded-lg bg-if-elevated border border-if-border text-sm text-if-text placeholder:text-if-muted focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      {/* Grid */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <p className="text-center text-sm text-if-muted py-16">Impossible de charger les créateurs.</p>
      ) : creators.length === 0 ? (
        <p className="text-center text-sm text-if-muted py-16">Aucun créateur trouvé pour « {debouncedQ} ».</p>
      ) : (
        <div
          className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 transition-opacity duration-150 ${isFetching ? "opacity-60" : "opacity-100"}`}
        >
          {creators.map((creator) => (
            <CreatorCard key={creator.id} creator={creator} onClick={() => setSelected(creator)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {(hasPrev || hasMore) && !isLoading && (
        <div className="flex items-center justify-center gap-3 mt-8">
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={!hasPrev}
            className="px-4 py-2 rounded-lg text-sm border border-if-border bg-if-elevated text-if-text hover:border-indigo-500 disabled:opacity-30 transition-colors"
          >
            ← Précédent
          </button>
          <span className="text-sm text-if-muted">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="px-4 py-2 rounded-lg text-sm border border-if-border bg-if-elevated text-if-text hover:border-indigo-500 disabled:opacity-30 transition-colors"
          >
            Suivant →
          </button>
        </div>
      )}

      {/* Modal */}
      {selected && (
        <CreatorModal
          name={selected.name}
          creatorId={selected.id}
          spriteCount={selected.sprite_count}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function CreatorCard({ creator, onClick }: { creator: CreatorOut; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-center gap-2 p-3 rounded-xl border border-if-border bg-if-elevated hover:border-indigo-500 hover:bg-if-elevated transition-all text-center"
    >
      <div className="w-10 h-10 rounded-full bg-indigo-950/60 border border-indigo-700/40 flex items-center justify-center shrink-0">
        <Palette size={16} className="text-indigo-400" />
      </div>
      <div className="min-w-0 w-full">
        <p className="text-xs font-medium text-if-text truncate group-hover:text-indigo-300 transition-colors">
          {creator.name}
        </p>
        <p className="text-[10px] text-if-muted mt-0.5">
          {creator.sprite_count} sprite{creator.sprite_count > 1 ? "s" : ""}
        </p>
      </div>
    </button>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
      {Array.from({ length: PAGE_SIZE }).map((_, i) => (
        <div key={i} className="flex flex-col items-center gap-2 p-3 rounded-xl border border-if-border bg-if-elevated animate-pulse">
          <div className="w-10 h-10 rounded-full bg-if-input" />
          <div className="w-full space-y-1">
            <div className="h-3 bg-if-input rounded w-3/4 mx-auto" />
            <div className="h-2 bg-if-input rounded w-1/2 mx-auto" />
          </div>
        </div>
      ))}
    </div>
  );
}
