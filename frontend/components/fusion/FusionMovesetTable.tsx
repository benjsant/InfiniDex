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
      <span
        title={headName}
        className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-900/60 border border-indigo-700/40 text-indigo-300"
      >
        H
      </span>
    );
  }
  return (
    <span
      title={bodyName}
      className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-900/60 border border-purple-700/40 text-purple-300"
    >
      B
    </span>
  );
}

function MoveRow({
  mv,
  showLevel,
  headName,
  bodyName,
}: {
  mv: FusionMoveOut;
  showLevel: boolean;
  headName: string;
  bodyName: string;
}) {
  return (
    <tr className="border-t border-[rgb(35,35,48)] hover:bg-[rgb(25,25,38)] transition-colors">
      {showLevel && (
        <td className="px-3 py-2 text-[rgb(120,120,140)] font-mono text-xs w-10">
          {mv.level ?? "—"}
        </td>
      )}
      <td className="px-3 py-2 font-medium text-[rgb(220,220,255)]">
        {mv.name_fr ?? mv.name_en}
        {mv.name_fr && (
          <span className="ml-1 text-xs text-[rgb(100,100,120)]">({mv.name_en})</span>
        )}
      </td>
      <td className="px-3 py-2">
        <TypeBadge typeName={mv.type.name_en} size="sm" />
      </td>
      <td className="px-3 py-2 text-[rgb(160,160,180)] text-xs">{formatCategory(mv.category)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{formatPower(mv.power)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{formatAccuracy(mv.accuracy)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{mv.pp}</td>
      <td className="px-3 py-2">
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
    <tr className="border-t border-[rgb(35,35,48)] hover:bg-[rgb(25,25,38)] transition-colors">
      <td className="px-3 py-2 font-medium text-[rgb(220,220,255)]">
        {mv.name_fr ?? mv.name_en}
        {mv.name_fr && (
          <span className="ml-1 text-xs text-[rgb(100,100,120)]">({mv.name_en})</span>
        )}
      </td>
      <td className="px-3 py-2">
        <TypeBadge typeName={mv.type.name_en} size="sm" />
      </td>
      <td className="px-3 py-2 text-[rgb(160,160,180)] text-xs">{formatCategory(mv.category)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{formatPower(mv.power)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{formatAccuracy(mv.accuracy)}</td>
      <td className="px-3 py-2 text-right font-mono text-[rgb(200,200,220)]">{mv.pp}</td>
      <td className="px-3 py-2 text-xs text-[rgb(140,140,180)]">{locationLabel}</td>
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
      <div className="flex flex-wrap items-center gap-3 text-xs text-[rgb(120,120,140)]">
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

      {/* Regular moves by method */}
      {METHOD_ORDER.map((method) => {
        const group = grouped[method];
        if (!group || group.length === 0) return null;
        const isLevelUp = method === "level_up";
        const sorted = [...group].sort((a, b) => (a.level ?? 0) - (b.level ?? 0));

        return (
          <div key={method}>
            <h3 className="text-sm font-semibold text-[rgb(160,160,180)] uppercase tracking-wider mb-2">
              {METHOD_LABELS[method]} ({group.length})
            </h3>
            <div className="overflow-x-auto rounded-lg border border-[rgb(40,40,55)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[rgb(25,25,35)] text-[rgb(120,120,140)] text-xs">
                    {isLevelUp && <th className="px-3 py-2 text-left w-10">Niv.</th>}
                    <th className="px-3 py-2 text-left">Capacité</th>
                    <th className="px-3 py-2 text-left">Type</th>
                    <th className="px-3 py-2 text-left">Cat.</th>
                    <th className="px-3 py-2 text-right">Puiss.</th>
                    <th className="px-3 py-2 text-right">Préc.</th>
                    <th className="px-3 py-2 text-right">PP</th>
                    <th className="px-3 py-2 text-left">Origine</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((mv, i) => (
                    <MoveRow
                      key={`${mv.move_id}-${i}`}
                      mv={mv}
                      showLevel={isLevelUp}
                      headName={headName}
                      bodyName={bodyName}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {/* Expert moves */}
      {expertMoves.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[rgb(160,160,180)] uppercase tracking-wider mb-2">
            Donneur expert ({expertMoves.length})
          </h3>
          <div className="overflow-x-auto rounded-lg border border-[rgb(40,40,55)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[rgb(25,25,35)] text-[rgb(120,120,140)] text-xs">
                  <th className="px-3 py-2 text-left">Capacité</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Cat.</th>
                  <th className="px-3 py-2 text-right">Puiss.</th>
                  <th className="px-3 py-2 text-right">Préc.</th>
                  <th className="px-3 py-2 text-right">PP</th>
                  <th className="px-3 py-2 text-left">Lieu</th>
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
