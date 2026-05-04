"use client";

import { useState, useMemo } from "react";
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

export default function MovesPage() {
  const { data: moves = [], isLoading } = useMoves();
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [catFilter, setCatFilter] = useState("");

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

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "#e1e4ff" }}>Capacités</h1>
        <Link
          href="/moves/tutors"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all self-start sm:self-auto if-panel if-glow-hover"
          style={{ color: "#6b7199" }}
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
          className="px-3 py-2 rounded-lg focus:outline-none"
          style={{ background: "#111428", border: "1px solid #1e2240", color: "#e1e4ff" }}
        >
          <option value="">Tous types</option>
          {TYPES_LIST.map((t) => <option key={t} value={t}>{TYPE_FR_NAMES[t] ?? t}</option>)}
        </select>
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="px-3 py-2 rounded-lg focus:outline-none"
          style={{ background: "#111428", border: "1px solid #1e2240", color: "#e1e4ff" }}
        >
          <option value="">Toutes catégories</option>
          <option value="Physical">Physique</option>
          <option value="Special">Spéciale</option>
          <option value="Status">Statut</option>
        </select>
      </div>

      <p className="text-sm mb-3" style={{ color: "#6b7199" }}>{filtered.length} capacités</p>

      {isLoading ? (
        <div className="animate-pulse space-y-2">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="h-10 bg-[rgb(25,25,35)] rounded" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid #1e2240" }}>
          <table className="w-full text-sm" style={{ minWidth: "360px" }}>
            <thead>
              <tr className="text-xs" style={{ background: "#0f1225", color: "#6b7199" }}>
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
              {filtered.map((mv) => (
                <tr
                  key={mv.id}
                  className="border-t hover:bg-[#1e2240] transition-colors"
                  style={{ borderColor: "#1a1d35" }}
                >
                  <td className="px-2 sm:px-3 py-2">
                    <span className="font-medium" style={{ color: "#e1e4ff" }}>
                      {mv.name_fr ?? mv.name_en}
                    </span>
                    {mv.name_fr && (
                      <span className="ml-1 text-xs hidden sm:inline" style={{ color: "#6b7199" }}>({mv.name_en})</span>
                    )}
                  </td>
                  <td className="px-2 sm:px-3 py-2">
                    <TypeBadge typeName={mv.type.name_en} label={mv.type.name_fr ?? mv.type.name_en} size="sm" />
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-xs" style={{ color: "#9aa0c0" }}>
                    {formatCategory(mv.category)}
                  </td>
                  <td className="px-2 sm:px-3 py-2 text-right font-mono text-xs" style={{ color: "#c8cbf0" }}>
                    {formatPower(mv.power)}
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "#c8cbf0" }}>
                    {formatAccuracy(mv.accuracy)}
                  </td>
                  <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "#c8cbf0" }}>
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
    </div>
  );
}
