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
        <h1 className="text-2xl font-bold text-[rgb(220,220,255)]">Créateurs de sprites</h1>
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
        <p className="text-center text-[rgb(120,120,140)] py-12">
          {displayQ ? `Aucun créateur trouvé pour "${displayQ}".` : "Aucun créateur."}
        </p>
      ) : (
        <>
          <p className="text-sm text-[rgb(120,120,140)] mb-4">
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
              className="px-4 py-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
            >
              <ChevronLeft size={16} className="inline" /> Précédent
            </button>
            <span className="px-4 py-2 text-[rgb(120,120,140)]">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={creators.length < PAGE_SIZE}
              className="px-4 py-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
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
      className="group flex flex-col items-center gap-2 p-4 rounded-xl bg-[rgb(18,18,26)] border border-[rgb(40,40,55)] hover:border-indigo-500 transition-all"
    >
      <div className="w-12 h-12 rounded-full bg-indigo-900/40 border border-indigo-700/30 flex items-center justify-center group-hover:border-indigo-500 transition-colors">
        <Users size={20} className="text-indigo-400" />
      </div>
      <p className="text-sm font-medium text-[rgb(200,200,220)] text-center truncate w-full">{creator.name}</p>
      <p className="text-xs text-[rgb(100,100,130)]">
        {creator.sprite_count.toLocaleString()} sprite{creator.sprite_count > 1 ? "s" : ""}
      </p>
    </Link>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      {Array.from({ length: 24 }).map((_, i) => (
        <div key={i} className="h-32 rounded-xl bg-[rgb(18,18,26)] border border-[rgb(40,40,55)] animate-pulse" />
      ))}
    </div>
  );
}
