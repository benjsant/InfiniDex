"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { GraduationCap, Search } from "lucide-react";
import { useMoves } from "@/hooks/useMoves";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { SearchBar } from "@/components/layout/SearchBar";
import { normalize, formatPower, formatAccuracy, formatCategory } from "@/lib/utils";
import { TYPE_FR_NAMES } from "@/lib/constants";

const TYPES_LIST = [
  "Normal","Fire","Water","Electric","Grass","Ice",
  "Fighting","Poison","Ground","Flying","Psychic","Bug",
  "Rock","Ghost","Dragon","Dark","Steel","Fairy",
];

const PAGE_SIZE = 50;

export default function MovesPage() {
  const { data: moves = [], isLoading } = useMoves();
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return moves.filter((m) => {
      if (typeFilter && m.type.name_en !== typeFilter) return false;
      if (catFilter && m.category !== catFilter) return false;
      if (q.trim().length >= 2) {
        const nq = normalize(q);
        if (!normalize(m.name_en).includes(nq) && !(m.name_fr && normalize(m.name_fr).includes(nq)))
          return false;
      }
      return true;
    });
  }, [moves, q, typeFilter, catFilter]);

  useEffect(() => { setPage(1); }, [q, typeFilter, catFilter]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold text-if-text">Capacités</h1>
        <Link
          href="/moves/tutors"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all self-start sm:self-auto if-panel if-glow-hover text-if-muted"
        >
          <GraduationCap size={14} />
          Maîtres des Capacités
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <SearchBar onSearch={setQ} placeholder="Rechercher une capacité…" className="flex-1" />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 rounded-lg focus:outline-none bg-if-card border border-if-border text-if-text"
        >
          <option value="">Tous types</option>
          {TYPES_LIST.map((t) => <option key={t} value={t}>{TYPE_FR_NAMES[t] ?? t}</option>)}
        </select>
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="px-3 py-2 rounded-lg focus:outline-none bg-if-card border border-if-border text-if-text"
        >
          <option value="">Toutes catégories</option>
          <option value="Physical">Physique</option>
          <option value="Special">Spéciale</option>
          <option value="Status">Statut</option>
        </select>
      </div>

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-if-muted">{filtered.length} capacités</p>
        {totalPages > 1 && (
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        )}
      </div>

      {isLoading ? (
        <div className="animate-pulse space-y-2">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="h-10 bg-if-elevated rounded" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-if-border">
          <table className="w-full text-sm" style={{ minWidth: "360px" }}>
            <thead>
              <tr className="text-xs bg-if-surface text-if-muted">
                <th className="px-2 sm:px-3 py-2 text-left">Capacité</th>
                <th className="px-2 sm:px-3 py-2 text-left">Type</th>
                <th className="hidden sm:table-cell px-3 py-2 text-left">Cat.</th>
                <th className="px-2 sm:px-3 py-2 text-right">Puiss.</th>
                <th className="hidden sm:table-cell px-3 py-2 text-right">Préc.</th>
                <th className="hidden sm:table-cell px-3 py-2 text-right">PP</th>
                <th className="px-2 py-2 w-8" />
              </tr>
            </thead>
            <tbody>
              {paginated.map((mv) => (
                <tr
                  key={mv.id}
                  className="border-t border-if-border-lo hover:bg-if-elevated transition-colors cursor-pointer"
                >
                  <td className="px-2 sm:px-3 py-2">
                    <Link href={`/moves/${mv.id}`} className="font-medium text-if-text hover:text-indigo-400 transition-colors">
                      {mv.name_fr ?? mv.name_en}
                    </Link>
                    {mv.name_fr && (
                      <span className="ml-1 text-xs hidden sm:inline text-if-muted">({mv.name_en})</span>
                    )}
                  </td>
                  <td className="px-2 sm:px-3 py-2">
                    <TypeBadge typeName={mv.type.name_en} label={mv.type.name_fr ?? mv.type.name_en} size="sm" />
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-xs text-if-text-xs">
                    {formatCategory(mv.category)}
                  </td>
                  <td className="px-2 sm:px-3 py-2 text-right font-mono text-xs text-if-text-dim">
                    {formatPower(mv.power)}
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs text-if-text-dim">
                    {formatAccuracy(mv.accuracy)}
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs text-if-text-dim">
                    {mv.pp ?? "—"}
                  </td>
                  <td className="px-2 py-2 text-center">
                    <Link
                      href={`/moves/${mv.id}`}
                      className="inline-flex items-center justify-center w-6 h-6 rounded hover:bg-indigo-500/20 text-if-muted hover:text-indigo-400 transition-colors"
                      title={mv.name_fr ?? mv.name_en}
                    >
                      <Search size={13} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && !isLoading && (
        <div className="mt-4 flex justify-center">
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      )}
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
      <span className="text-xs text-if-muted px-2">
        {page} / {totalPages}
      </span>
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
