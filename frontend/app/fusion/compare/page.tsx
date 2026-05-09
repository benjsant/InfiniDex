"use client";

import Link from "next/link";
import { GitCompare, Trash2, ArrowLeft } from "lucide-react";
import { useFusion } from "@/hooks/useFusion";
import { useComparison } from "@/hooks/useComparison";
import { FusionSprite } from "@/components/fusion/FusionSprite";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import type { FusionResult } from "@/types/api";

const STAT_KEYS: { key: keyof FusionResult; label: string }[] = [
  { key: "hp",         label: "HP"     },
  { key: "attack",     label: "Atk"    },
  { key: "defense",    label: "Déf"    },
  { key: "sp_attack",  label: "AtkSpé" },
  { key: "sp_defense", label: "DéfSpé" },
  { key: "speed",      label: "Vit"    },
];

function StatRow({
  label,
  a,
  b,
}: {
  label: string;
  a: number;
  b: number;
}) {
  const max = Math.max(a, b, 1);
  const aWins = a > b;
  const bWins = b > a;

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 py-1.5">
      {/* Left stat */}
      <div className="flex items-center justify-end gap-2">
        <span
          className="text-sm font-mono font-bold w-8 text-right"
          style={{ color: aWins ? "#4ade80" : "#e1e4ff" }}
        >
          {a}
        </span>
        <div className="h-2 rounded-full flex-1 max-w-[80px]" style={{ background: "#1e2240" }}>
          <div
            className="h-full rounded-full ml-auto"
            style={{
              width: `${Math.round((a / max) * 100)}%`,
              background: aWins ? "#4ade80" : "#6366f1",
            }}
          />
        </div>
      </div>

      {/* Label */}
      <span className="text-xs text-center w-14 shrink-0" style={{ color: "#6b7199" }}>
        {label}
      </span>

      {/* Right stat */}
      <div className="flex items-center gap-2">
        <div className="h-2 rounded-full flex-1 max-w-[80px]" style={{ background: "#1e2240" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.round((b / max) * 100)}%`,
              background: bWins ? "#4ade80" : "#6366f1",
            }}
          />
        </div>
        <span
          className="text-sm font-mono font-bold w-8"
          style={{ color: bWins ? "#4ade80" : "#e1e4ff" }}
        >
          {b}
        </span>
      </div>
    </div>
  );
}

function FusionColumn({ fusion }: { fusion: FusionResult }) {
  const total = STAT_KEYS.reduce((s, { key }) => s + (fusion[key] as number), 0);
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="w-28 h-28 flex items-center justify-center rounded-xl"
        style={{ background: "#090c1a", border: "1px solid #1e2240" }}
      >
        <FusionSprite headId={fusion.head_id} bodyId={fusion.body_id} size={104} />
      </div>
      <div className="text-center">
        <p className="font-semibold text-sm" style={{ color: "#e1e4ff" }}>
          {fusion.head_name_en}/{fusion.body_name_en}
        </p>
        <div className="flex gap-1 justify-center mt-1">
          {fusion.type1 && <TypeBadge typeName={fusion.type1.name_en} size="sm" />}
          {fusion.type2 && <TypeBadge typeName={fusion.type2.name_en} size="sm" />}
        </div>
        <p className="text-xs mt-1" style={{ color: "#6b7199" }}>
          Total{" "}
          <span className="font-mono font-bold" style={{ color: "#c8cbf0" }}>
            {total}
          </span>
        </p>
      </div>
    </div>
  );
}

function ComparePanel({
  slotA,
  slotB,
}: {
  slotA: { headId: number; bodyId: number };
  slotB: { headId: number; bodyId: number };
}) {
  const { data: fusionA, isLoading: loadA } = useFusion(slotA.headId, slotA.bodyId);
  const { data: fusionB, isLoading: loadB } = useFusion(slotB.headId, slotB.bodyId);

  if (loadA || loadB) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-32 bg-[#111428] rounded-xl" />
        <div className="h-48 bg-[#111428] rounded-xl" />
      </div>
    );
  }

  if (!fusionA || !fusionB) {
    return (
      <p className="text-center py-12" style={{ color: "#6b7199" }}>
        Impossible de charger une des fusions.
      </p>
    );
  }

  const totalA = STAT_KEYS.reduce((s, { key }) => s + (fusionA[key] as number), 0);
  const totalB = STAT_KEYS.reduce((s, { key }) => s + (fusionB[key] as number), 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
        <Link href={`/fusion/${slotA.headId}/${slotA.bodyId}`}>
          <FusionColumn fusion={fusionA} />
        </Link>
        <span className="text-lg font-bold" style={{ color: "#2d3260" }}>VS</span>
        <Link href={`/fusion/${slotB.headId}/${slotB.bodyId}`}>
          <FusionColumn fusion={fusionB} />
        </Link>
      </div>

      {/* Stats */}
      <div className="rounded-xl p-4" style={{ background: "#111428", border: "1px solid #1e2240" }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#6b7199" }}>
          Statistiques
        </p>
        <div className="divide-y" style={{ borderColor: "#1a1d35" }}>
          {STAT_KEYS.map(({ key, label }) => (
            <StatRow
              key={key}
              label={label}
              a={fusionA[key] as number}
              b={fusionB[key] as number}
            />
          ))}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 pt-3 mt-1 border-t" style={{ borderColor: "#1e2240" }}>
          <span
            className="text-sm font-bold font-mono text-right"
            style={{ color: totalA > totalB ? "#4ade80" : "#e1e4ff" }}
          >
            {totalA}
          </span>
          <span className="text-xs text-center w-14" style={{ color: "#6b7199" }}>Total</span>
          <span
            className="text-sm font-bold font-mono"
            style={{ color: totalB > totalA ? "#4ade80" : "#e1e4ff" }}
          >
            {totalB}
          </span>
        </div>
      </div>

      {/* Type comparison */}
      <div className="rounded-xl p-4" style={{ background: "#111428", border: "1px solid #1e2240" }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#6b7199" }}>
          Types
        </p>
        <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
          <div className="flex gap-1 justify-end">
            {fusionA.type1 && <TypeBadge typeName={fusionA.type1.name_en} />}
            {fusionA.type2 && <TypeBadge typeName={fusionA.type2.name_en} />}
          </div>
          <span className="text-xs w-4 text-center" style={{ color: "#2d3260" }}>vs</span>
          <div className="flex gap-1">
            {fusionB.type1 && <TypeBadge typeName={fusionB.type1.name_en} />}
            {fusionB.type2 && <TypeBadge typeName={fusionB.type2.name_en} />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const { slots, clearComparison, canCompare } = useComparison();

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Link
            href="/fusion"
            className="text-sm transition-colors hover:text-[#e8b84b]"
            style={{ color: "#6b7199" }}
          >
            <ArrowLeft size={14} className="inline mr-1" />
            Fusion
          </Link>
          <span style={{ color: "#2d3260" }}>/</span>
          <span className="text-sm flex items-center gap-1.5" style={{ color: "#e1e4ff" }}>
            <GitCompare size={14} />
            Comparaison
          </span>
        </div>
        {(slots[0] || slots[1]) && (
          <button
            onClick={clearComparison}
            className="flex items-center gap-1 text-xs transition-colors hover:text-red-400"
            style={{ color: "#6b7199" }}
          >
            <Trash2 size={12} />
            Réinitialiser
          </button>
        )}
      </div>

      {!canCompare ? (
        <div className="text-center py-16 space-y-3">
          <GitCompare size={32} className="mx-auto" style={{ color: "#2d3260" }} />
          <p style={{ color: "#6b7199" }}>
            {slots[0]
              ? `"${slots[0].headName}/${slots[0].bodyName}" sélectionné — choisis une deuxième fusion.`
              : "Sélectionne deux fusions à comparer depuis leurs pages de détail."}
          </p>
          <Link
            href="/fusion"
            className="inline-block mt-2 text-sm px-4 py-2 rounded-lg transition-all bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            Aller au calculateur
          </Link>
        </div>
      ) : (
        <ComparePanel slotA={slots[0]!} slotB={slots[1]!} />
      )}
    </div>
  );
}
