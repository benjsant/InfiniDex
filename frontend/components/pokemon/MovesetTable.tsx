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
            <h3 className="text-sm font-semibold text-[rgb(160,160,180)] uppercase tracking-wider mb-2">
              {METHOD_LABELS[method] ?? method} ({group.length})
            </h3>
            <div className="overflow-x-auto rounded-lg border border-[rgb(40,40,55)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[rgb(25,25,35)] text-[rgb(120,120,140)] text-xs">
                    {method === "level_up" && <th className="px-3 py-2 text-left">Niv.</th>}
                    <th className="px-3 py-2 text-left">Capacité</th>
                    <th className="px-3 py-2 text-left">Type</th>
                    <th className="px-3 py-2 text-left">Cat.</th>
                    <th className="px-3 py-2 text-right">Puiss.</th>
                    <th className="px-3 py-2 text-right">Préc.</th>
                    <th className="px-3 py-2 text-right">PP</th>
                    <th className="px-3 py-2 text-left">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {[...group]
                    .sort((a, b) => (a.level ?? 0) - (b.level ?? 0))
                    .map((mv, i) => (
                      <tr
                        key={`${mv.move_id}-${i}`}
                        className="border-t border-[rgb(35,35,48)] hover:bg-[rgb(25,25,38)] transition-colors"
                      >
                        {method === "level_up" && (
                          <td className="px-3 py-2 text-[rgb(120,120,140)] font-mono text-xs">
                            {mv.level ?? "—"}
                          </td>
                        )}
                        <td className="px-3 py-2 font-medium text-[rgb(220,220,255)]">
                          {mv.name_fr ?? mv.name_en}
                          {mv.name_fr && (
                            <span className="ml-1 text-xs text-[rgb(100,100,120)]">
                              ({mv.name_en})
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <TypeBadge typeName={mv.type.name_en} size="sm" />
                        </td>
                        <td className="px-3 py-2 text-[rgb(160,160,180)] text-xs">
                          {formatCategory(mv.category)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">
                          {formatPower(mv.power)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">
                          {formatAccuracy(mv.accuracy)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">
                          {mv.pp ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              mv.source === "infinite_fusion"
                                ? "bg-indigo-900/40 text-indigo-300"
                                : "bg-[rgb(35,35,50)] text-[rgb(120,120,140)]"
                            }`}
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
