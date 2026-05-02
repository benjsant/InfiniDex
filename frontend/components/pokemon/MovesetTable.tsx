"use client";

import { useMemo } from "react";
import type { PokemonMoveOut } from "@/types/api";
import { TypeBadge } from "./TypeBadge";
import { formatCategory, formatMethod, formatPower, formatAccuracy } from "@/lib/utils";
import { METHOD_LABELS } from "@/lib/constants";

interface MovesetTableProps {
  moves: PokemonMoveOut[];
}

const METHOD_ORDER = ["level_up", "tm", "breeding", "tutor", "before_evolution"];

export function MovesetTable({ moves }: MovesetTableProps) {
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

        return (
          <div key={method}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-2" style={{ color: "#6b7199" }}>
              {METHOD_LABELS[method] ?? method} ({group.length})
            </h3>
            <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid #1e2240" }}>
              <table className="w-full text-sm" style={{ minWidth: "400px" }}>
                <thead>
                  <tr className="text-xs" style={{ background: "#0f1225", color: "#6b7199" }}>
                    {method === "level_up" && <th className="px-2 sm:px-3 py-2 text-left w-8">Niv.</th>}
                    <th className="px-2 sm:px-3 py-2 text-left">Capacité</th>
                    <th className="px-2 sm:px-3 py-2 text-left">Type</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-left">Cat.</th>
                    <th className="px-2 sm:px-3 py-2 text-right">Puiss.</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-right">Préc.</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-right">PP</th>
                    <th className="hidden md:table-cell px-3 py-2 text-left">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {[...group]
                    .sort((a, b) => (a.level ?? 0) - (b.level ?? 0))
                    .map((mv, i) => (
                      <tr
                        key={`${mv.move_id}-${i}`}
                        className="border-t hover:bg-[#1e2240] transition-colors"
                        style={{ borderColor: "#1a1d35" }}
                      >
                        {method === "level_up" && (
                          <td className="px-2 sm:px-3 py-2 font-mono text-xs w-8" style={{ color: "#6b7199" }}>
                            {mv.level ?? "—"}
                          </td>
                        )}
                        <td className="px-2 sm:px-3 py-2 font-medium" style={{ color: "#e1e4ff" }}>
                          <span>{mv.name_fr ?? mv.name_en}</span>
                          {mv.name_fr && (
                            <span className="ml-1 text-xs hidden sm:inline" style={{ color: "#6b7199" }}>
                              ({mv.name_en})
                            </span>
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
                        <td className="hidden md:table-cell px-3 py-2">
                          <span
                            className="text-xs px-1.5 py-0.5 rounded"
                            style={
                              mv.source === "infinite_fusion"
                                ? { background: "rgba(232,184,75,0.12)", color: "#e8b84b", border: "1px solid rgba(232,184,75,0.3)" }
                                : { background: "#1e2240", color: "#6b7199" }
                            }
                          >
                            {mv.source === "infinite_fusion" ? "IF" : "Base"}
                          </span>
                        </td>
                      </tr>
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
