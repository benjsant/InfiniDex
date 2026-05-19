"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getAbilities, getAbility } from "@/lib/api";
import { SearchBar } from "@/components/layout/SearchBar";
import { normalize } from "@/lib/utils";

const PAGE_SIZE = 40;

export default function AbilitiesPage() {
  const { data: abilities = [], isLoading, isError } = useQuery({
    queryKey: ["abilities"],
    queryFn: getAbilities,
    staleTime: Infinity,
  });

  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const { data: detail } = useQuery({
    queryKey: ["ability", selectedId],
    queryFn: () => getAbility(selectedId!),
    enabled: selectedId != null,
  });

  const filtered = useMemo(() => {
    if (q.trim().length < 2) return abilities;
    const nq = normalize(q);
    return abilities.filter(
      (a) =>
        normalize(a.name_en).includes(nq) ||
        (a.name_fr && normalize(a.name_fr).includes(nq)),
    );
  }, [abilities, q]);

  useEffect(() => { setPage(1); }, [q]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-6 text-if-text">Talents</h1>

      <SearchBar onSearch={setQ} placeholder="Rechercher un talent…" className="mb-4" />

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-if-text-xs">{filtered.length} talents</p>
        {totalPages > 1 && (
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        {/* List */}
        <div className="flex-1 rounded-lg border border-if-border">
          {isLoading ? (
            <div className="animate-pulse p-4 space-y-2">
              {Array.from({ length: 15 }).map((_, i) => (
                <div key={i} className="h-10 bg-if-elevated rounded" />
              ))}
            </div>
          ) : isError ? (
            <p className="p-6 text-sm text-center" style={{ color: "var(--color-if-muted)" }}>Impossible de charger les talents.</p>
          ) : (
            paginated.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedId(selectedId === a.id ? null : a.id)}
                className="w-full flex items-center justify-between px-4 py-3 border-b border-if-border-lo hover:bg-if-elevated transition-colors text-left"
                style={selectedId === a.id ? { borderLeft: "2px solid var(--color-if-accent)", background: "var(--color-if-surface)" } : undefined}
              >
                <div>
                  <p className="text-sm font-medium text-if-text">{a.name_fr ?? a.name_en}</p>
                  {a.name_fr && <p className="text-xs text-if-muted">{a.name_en}</p>}
                </div>
                <Link
                  href={`/abilities/${a.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center justify-center w-7 h-7 rounded hover:bg-indigo-500/20 text-if-muted hover:text-indigo-400 transition-colors ml-2 shrink-0"
                  title={a.name_fr ?? a.name_en}
                >
                  <Search size={14} />
                </Link>
              </button>
            ))
          )}

          {totalPages > 1 && !isLoading && (
            <div className="flex justify-center py-3">
              <Pagination page={page} totalPages={totalPages} onChange={setPage} />
            </div>
          )}
        </div>

        {/* Detail panel */}
        {detail && (
          <div className="w-full md:w-72 shrink-0 rounded-lg p-4 h-fit md:sticky top-20 if-panel">
            <h2 className="font-bold mb-0.5 text-if-text">{detail.name_fr ?? detail.name_en}</h2>
            {detail.name_fr && (
              <p className="text-xs mb-3 text-if-muted">{detail.name_en}</p>
            )}
            {detail.description_fr && (
              <p className="text-sm mb-2 text-if-text-dim">{detail.description_fr}</p>
            )}
            {detail.description_en && (
              <p className="text-sm pt-2 mt-2 text-if-muted border-t border-if-border">
                {detail.description_en}
              </p>
            )}
            <Link
              href={`/abilities/${detail.id}`}
              className="mt-3 block text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Voir la page complète →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        className="px-2 py-1 rounded text-xs text-if-muted hover:text-if-text disabled:opacity-30 transition-colors"
      >
        ‹
      </button>
      <span className="text-xs text-if-muted px-2">{page} / {totalPages}</span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
        className="px-2 py-1 rounded text-xs text-if-muted hover:text-if-text disabled:opacity-30 transition-colors"
      >
        ›
      </button>
    </div>
  );
}
