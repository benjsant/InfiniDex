"use client";

import { useMemo } from "react";
import type { FusionMoveOut, FusionExpertMoveOut } from "@/types/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { formatCategory, formatPower, formatAccuracy } from "@/lib/utils";

interface FusionMovesetTableProps {
  moves: FusionMoveOut[];
  expertMoves: FusionExpertMoveOut[];
  headName: string;
  bodyName: string;
}

const METHOD_ORDER = ["level_up", "breeding", "tutor", "tm", "before_evolution"];

const METHOD_LABELS: Record<string, string> = {
  level_up:         "Par niveau",
  breeding:         "Reproduction",
  tutor:            "Donneur de capacités",
  tm:               "CT/CS",
  before_evolution: "Pré-évolution",
};

function OriginPill({ origin, headName, bodyName }: { origin: "head" | "body" | "both"; headName: string; bodyName: string }) {
  if (origin === "both") {
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r from-indigo-900/60 to-purple-900/60 border border-indigo-700/40 text-indigo-200">
        H+B
      </span>
    );
  }
  if (origin === "head") {
    return (
      <span title={headName} className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-900/60 border border-indigo-700/40 text-indigo-300">
        H
      </span>
    );
  }
  return (
    <span title={bodyName} className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-900/60 border border-purple-700/40 text-purple-300">
      B
    </span>
  );
}

function MoveRow({ mv, showLevel, headName, bodyName }: { mv: FusionMoveOut; showLevel: boolean; headName: string; bodyName: string }) {
  return (
    <tr className="border-t hover:bg-if-border transition-colors" style={{ borderColor: "var(--color-if-border-lo)" }}>
      {showLevel && (
        <td className="px-2 sm:px-3 py-2 font-mono text-xs w-8" style={{ color: "var(--color-if-muted)" }}>
          {mv.level ?? "—"}
        </td>
      )}
      <td className="px-2 sm:px-3 py-2 font-medium" style={{ color: "var(--color-if-text)" }}>
        <span>{mv.name_fr ?? mv.name_en}</span>
        {mv.name_fr && (
          <span className="ml-1 text-xs hidden sm:inline" style={{ color: "var(--color-if-muted)" }}>({mv.name_en})</span>
        )}
      </td>
      <td className="px-2 sm:px-3 py-2">
        <TypeBadge typeName={mv.type.name_en} label={mv.type.name_fr ?? mv.type.name_en} size="sm" />
      </td>
      <td className="hidden sm:table-cell px-3 py-2 text-xs" style={{ color: "var(--color-if-text-lo)" }}>{formatCategory(mv.category)}</td>
      <td className="px-2 sm:px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{formatPower(mv.power)}</td>
      <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{formatAccuracy(mv.accuracy)}</td>
      <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{mv.pp}</td>
      <td className="px-2 sm:px-3 py-2">
        <OriginPill origin={mv.origin} headName={headName} bodyName={bodyName} />
      </td>
    </tr>
  );
}

function ExpertMoveRow({ mv }: { mv: FusionExpertMoveOut }) {
  const locationLabel = mv.locations.includes("knot_island") && mv.locations.includes("boon_island")
    ? "Knot + Boon"
    : mv.locations.includes("knot_island")
      ? "Knot Island"
      : "Boon Island";

  return (
    <tr className="border-t hover:bg-if-border transition-colors" style={{ borderColor: "var(--color-if-border-lo)" }}>
      <td className="px-2 sm:px-3 py-2 font-medium" style={{ color: "var(--color-if-text)" }}>
        <span>{mv.name_fr ?? mv.name_en}</span>
        {mv.name_fr && (
          <span className="ml-1 text-xs hidden sm:inline" style={{ color: "var(--color-if-muted)" }}>({mv.name_en})</span>
        )}
      </td>
      <td className="px-2 sm:px-3 py-2">
        <TypeBadge typeName={mv.type.name_en} label={mv.type.name_fr ?? mv.type.name_en} size="sm" />
      </td>
      <td className="hidden sm:table-cell px-3 py-2 text-xs" style={{ color: "var(--color-if-text-lo)" }}>{formatCategory(mv.category)}</td>
      <td className="px-2 sm:px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{formatPower(mv.power)}</td>
      <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{formatAccuracy(mv.accuracy)}</td>
      <td className="hidden sm:table-cell px-3 py-2 text-right font-mono text-xs" style={{ color: "var(--color-if-text-dim)" }}>{mv.pp}</td>
      <td className="hidden sm:table-cell px-3 py-2 text-xs" style={{ color: "var(--color-if-text-lo)" }}>{locationLabel}</td>
    </tr>
  );
}

export function FusionMovesetTable({ moves, expertMoves, headName, bodyName }: FusionMovesetTableProps) {
  const grouped = useMemo(
    () =>
      METHOD_ORDER.reduce<Record<string, FusionMoveOut[]>>((acc, m) => {
        acc[m] = moves.filter((mv) => mv.method === m);
        return acc;
      }, {}),
    [moves],
  );

  const totalMoves = moves.length + expertMoves.length;
  if (totalMoves === 0) return null;

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: "var(--color-if-muted)" }}>
        <span className="font-semibold">Origine :</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-900/60 border border-indigo-700/40 text-indigo-300">H</span>
          {headName} (tête)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-900/60 border border-purple-700/40 text-purple-300">B</span>
          {bodyName} (corps)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r from-indigo-900/60 to-purple-900/60 border border-indigo-700/40 text-indigo-200">H+B</span>
          les deux
        </span>
      </div>

      {METHOD_ORDER.map((method) => {
        const group = grouped[method];
        if (!group || group.length === 0) return null;
        const isLevelUp = method === "level_up";
        const sorted = [...group].sort((a, b) => (a.level ?? 0) - (b.level ?? 0));

        return (
          <div key={method}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-if-muted)" }}>
              {METHOD_LABELS[method]} ({group.length})
            </h3>
            <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid var(--color-if-border)" }}>
              <table className="w-full text-sm" style={{ minWidth: isLevelUp ? "380px" : "340px" }}>
                <thead>
                  <tr className="text-xs" style={{ background: "var(--color-if-surface)", color: "var(--color-if-muted)" }}>
                    {isLevelUp && <th className="px-2 sm:px-3 py-2 text-left w-8">Niv.</th>}
                    <th className="px-2 sm:px-3 py-2 text-left">Capacité</th>
                    <th className="px-2 sm:px-3 py-2 text-left">Type</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-left">Cat.</th>
                    <th className="px-2 sm:px-3 py-2 text-right">Puiss.</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-right">Préc.</th>
                    <th className="hidden sm:table-cell px-3 py-2 text-right">PP</th>
                    <th className="px-2 sm:px-3 py-2 text-left">Orig.</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((mv, i) => (
                    <MoveRow key={`${mv.move_id}-${i}`} mv={mv} showLevel={isLevelUp} headName={headName} bodyName={bodyName} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {expertMoves.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-if-muted)" }}>
            Donneur expert ({expertMoves.length})
          </h3>
          <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid var(--color-if-border)" }}>
            <table className="w-full text-sm" style={{ minWidth: "340px" }}>
              <thead>
                <tr className="text-xs" style={{ background: "var(--color-if-surface)", color: "var(--color-if-muted)" }}>
                  <th className="px-2 sm:px-3 py-2 text-left">Capacité</th>
                  <th className="px-2 sm:px-3 py-2 text-left">Type</th>
                  <th className="hidden sm:table-cell px-3 py-2 text-left">Cat.</th>
                  <th className="px-2 sm:px-3 py-2 text-right">Puiss.</th>
                  <th className="hidden sm:table-cell px-3 py-2 text-right">Préc.</th>
                  <th className="hidden sm:table-cell px-3 py-2 text-right">PP</th>
                  <th className="hidden sm:table-cell px-3 py-2 text-left">Lieu</th>
                </tr>
              </thead>
              <tbody>
                {expertMoves.map((mv, i) => (
                  <ExpertMoveRow key={`expert-${mv.move_id}-${i}`} mv={mv} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
