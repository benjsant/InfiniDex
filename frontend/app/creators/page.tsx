"use client";

import { useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Users, ChevronLeft, ChevronRight } from "lucide-react";
import { SearchBar } from "@/components/layout/SearchBar";
import { getCreators } from "@/lib/api";
import type { CreatorOut } from "@/types/api";

const PAGE_SIZE = 48;

export default function CreatorsPage() {
  return (
    <Suspense>
      <CreatorsContent />
    </Suspense>
  );
}

function CreatorsContent() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [page, setPage] = useState(1);

  const { data: creators = [], isLoading } = useQuery<CreatorOut[]>({
    queryKey: ["creators", q, page],
    queryFn: () => getCreators({ q: q.trim() || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    staleTime: Infinity,
  });

  const displayQ = useMemo(() => q.trim(), [q]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-5">
        <Users size={22} className="text-indigo-400" />
        <h1 className="text-2xl font-bold text-if-text-hi">Créateurs de sprites</h1>
      </div>

      <div className="mb-6">
        <SearchBar
          onSearch={(v) => { setQ(v); setPage(1); }}
          placeholder="Rechercher un créateur…"
          className="max-w-sm"
        />
      </div>

      {isLoading ? (
        <SkeletonGrid />
      ) : creators.length === 0 ? (
        <p className="text-center text-if-text-xs py-12">
          {displayQ ? `Aucun créateur trouvé pour "${displayQ}".` : "Aucun créateur."}
        </p>
      ) : (
        <>
          <p className="text-sm text-if-text-xs mb-4">
            {creators.length} créateur{creators.length > 1 ? "s" : ""}
            {displayQ ? ` pour "${displayQ}"` : ""}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {creators.map((c) => (
              <CreatorCard key={c.id} creator={c} />
            ))}
          </div>

          <div className="flex justify-center gap-3 mt-8">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-lo disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
            >
              <ChevronLeft size={16} className="inline" /> Précédent
            </button>
            <span className="px-4 py-2 text-if-text-xs">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={creators.length < PAGE_SIZE}
              className="px-4 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-lo disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
            >
              Suivant <ChevronRight size={16} className="inline" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function CreatorCard({ creator }: { creator: CreatorOut }) {
  return (
    <Link
      href={`/creators/${creator.id}`}
      className="group flex flex-col items-center gap-2 p-4 rounded-xl bg-if-surface border border-if-border-lo hover:border-indigo-500 transition-all"
    >
      <div className="w-12 h-12 rounded-full bg-indigo-900/40 border border-indigo-700/30 flex items-center justify-center group-hover:border-indigo-500 transition-colors">
        <Users size={20} className="text-indigo-400" />
      </div>
      <p className="text-sm font-medium text-if-text-dim text-center truncate w-full">{creator.name}</p>
      <p className="text-xs text-if-muted">
        {creator.sprite_count.toLocaleString()} sprite{creator.sprite_count > 1 ? "s" : ""}
      </p>
    </Link>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      {Array.from({ length: 24 }).map((_, i) => (
        <div key={i} className="h-32 rounded-xl bg-if-surface border border-if-border-lo animate-pulse" />
      ))}
    </div>
  );
}
