"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, X } from "lucide-react";
import Link from "next/link";
import type { PokemonMoveOut } from "@/types/api";
import { TypeBadge } from "./TypeBadge";
import { formatCategory, formatMethod, formatPower, formatAccuracy } from "@/lib/utils";
import { METHOD_LABELS } from "@/lib/constants";
import { getMove } from "@/lib/api";

interface MovesetTableProps {
  moves: PokemonMoveOut[];
}

const METHOD_ORDER = ["level_up", "tm", "breeding", "tutor", "before_evolution"];

function MoveDetailRow({ moveId, colSpan }: { moveId: number; colSpan: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["move", moveId],
    queryFn: () => getMove(moveId),
    staleTime: Infinity,
  });

  return (
    <tr style={{ background: "var(--color-if-surface)" }}>
      <td colSpan={colSpan} className="px-4 py-2.5">
        {isLoading ? (
          <div className="h-4 w-48 animate-pulse rounded" style={{ background: "var(--color-if-border)" }} />
        ) : data ? (
          <div className="flex items-start justify-between gap-4">
            <div className="text-xs" style={{ color: "var(--color-if-text-dim)" }}>
              {data.description_fr ?? data.description_en ?? <span style={{ color: "var(--color-if-muted)" }}>Aucune description disponible.</span>}
              {data.description_fr && data.description_en && (
                <span className="ml-2 text-xs" style={{ color: "var(--color-if-muted)" }}>({data.description_en})</span>
              )}
            </div>
            <Link
              href={`/moves/${moveId}`}
              className="shrink-0 text-xs hover:underline"
              style={{ color: "var(--color-if-accent)" }}
            >
              Fiche complète →
            </Link>
          </div>
        ) : null}
      </td>
    </tr>
  );
}

export function MovesetTable({ moves }: MovesetTableProps) {
  const [openMoveId, setOpenMoveId] = useState<number | null>(null);

  const grouped = useMemo(
    () =>
      METHOD_ORDER.reduce<Record<string, PokemonMoveOut[]>>((acc, m) => {
        acc[m] = moves.filter((mv) => mv.method === m);
        return acc;
      }, {}),
    [moves],
  );

  return (
    <div className="space-y-6">
      {METHOD_ORDER.map((method) => {
        const group = grouped[method];
        if (!group || group.length === 0) return null;

        const hasLevel = method === "level_up";
        const colSpan = hasLevel ? 9 : 8;

        return (
          <div key={method}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-if-muted)" }}>
              {METHOD_LABELS[method] ?? method} ({group.length})
            </h3>
            <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid var(--color-if-border)" }}>
              <table className="w-full text-sm" style={{ minWidth: "400px" }}>
                <thead>
                  <tr className="text-xs" style={{ background: "var(--color-if-surface)", color: "var(--color-if-muted)" }}>
                    {hasLevel && <th className="px-2 sm:px-3 py-2 text-left w-8">Niv.</th>}
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
                  {[...group]
                    .sort((a, b) => (a.level ?? 0) - (b.level ?? 0))
                    .map((mv, i) => (
                      <>
                        <tr
                          key={`${mv.move_id}-${i}`}
                          className="border-t hover:bg-if-border transition-colors"
                          style={{ borderColor: "var(--color-if-border-lo)" }}
                        >
                          {hasLevel && (
                            <td className="px-2 sm:px-3 py-2 font-mono text-xs w-8" style={{ color: "var(--color-if-muted)" }}>
                              {mv.level ?? "—"}
                            </td>
                          )}
                          <td className="px-2 sm:px-3 py-2 font-medium" style={{ color: "var(--color-if-text)" }}>
                            <span>{mv.name_fr ?? mv.name_en}</span>
                            {mv.name_fr && (
                              <span className="ml-1 text-xs hidden sm:inline" style={{ color: "var(--color-if-muted)" }}>
                                ({mv.name_en})
                              </span>
                            )}
                          </td>
                          <td className="px-2 sm:px-3 py-2">
                            <TypeBadge typeName={mv.type.name_en} label={mv.type.name_fr ?? mv.type.name_en} size="sm" />
                          </td>
                          <td className="hidden sm:table-cell px-3 py-2 text-xs" style={{ color: "var(--color-if-text-lo)" }}>
                            {formatCategory(mv.category)}
                          </td>
                          <td className="px-2 sm:px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>
                            {formatPower(mv.power)}
                          </td>
                          <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>
                            {formatAccuracy(mv.accuracy)}
                          </td>
                          <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>
                            {mv.pp ?? "—"}
                          </td>
                          <td className="px-2 py-2 text-center">
                            <button
                              onClick={() => setOpenMoveId(openMoveId === mv.move_id ? null : mv.move_id)}
                              className="inline-flex items-center justify-center w-6 h-6 rounded transition-colors"
                              style={
                                openMoveId === mv.move_id
                                  ? { background: "rgba(99,102,241,0.2)", color: "var(--color-if-accent)" }
                                  : { color: "var(--color-if-muted)" }
                              }
                              title="Voir la description"
                            >
                              {openMoveId === mv.move_id ? <X size={12} /> : <Info size={12} />}
                            </button>
                          </td>
                        </tr>
                        {openMoveId === mv.move_id && (
                          <MoveDetailRow key={`detail-${mv.move_id}`} moveId={mv.move_id} colSpan={colSpan} />
                        )}
                      </>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
