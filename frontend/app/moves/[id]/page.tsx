"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Zap } from "lucide-react";
import { getMove } from "@/lib/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { formatPower, formatAccuracy, formatCategory } from "@/lib/utils";

function StatRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-if-border-lo last:border-0">
      <span className="text-sm text-if-muted">{label}</span>
      <span className="text-sm font-medium text-if-text">{value ?? "—"}</span>
    </div>
  );
}

export default function MoveDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const moveId = Number(id);

  const { data: move, isLoading, isError } = useQuery({
    queryKey: ["move", moveId],
    queryFn: () => getMove(moveId),
    enabled: !isNaN(moveId),
  });

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6 animate-pulse space-y-4">
        <div className="h-8 w-48 bg-if-elevated rounded" />
        <div className="h-4 w-32 bg-if-elevated rounded" />
        <div className="h-40 bg-if-elevated rounded-xl" />
      </div>
    );
  }

  if (isError || !move) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <p className="text-if-muted">Capacité introuvable.</p>
        <Link href="/moves" className="mt-4 inline-flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300">
          <ArrowLeft size={14} /> Retour aux capacités
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <Link
        href="/moves"
        className="inline-flex items-center gap-1.5 text-sm text-if-muted hover:text-if-text transition-colors mb-6"
      >
        <ArrowLeft size={14} />
        Capacités
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <div className="p-3 rounded-xl bg-indigo-600/20 border border-indigo-500/30 shrink-0">
          <Zap size={24} className="text-indigo-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-if-text-hi">
            {move.name_fr ?? move.name_en}
          </h1>
          {move.name_fr && (
            <p className="text-if-muted text-sm mt-0.5">{move.name_en}</p>
          )}
          <div className="mt-2">
            <TypeBadge typeName={move.type.name_en} label={move.type.name_fr ?? move.type.name_en} />
          </div>
        </div>
      </div>

      {/* Stats card */}
      <div className="if-panel p-4 mb-4">
        <StatRow label="Catégorie"  value={formatCategory(move.category)} />
        <StatRow label="Puissance"  value={formatPower(move.power)} />
        <StatRow label="Précision"  value={formatAccuracy(move.accuracy)} />
        <StatRow label="PP"         value={move.pp} />
        <StatRow label="Source"     value={move.source} />
      </div>

      {/* Descriptions */}
      {(move.description_fr || move.description_en) && (
        <div className="if-panel p-4 space-y-3">
          {move.description_fr && (
            <div>
              <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-1">Description (FR)</p>
              <p className="text-sm text-if-text leading-relaxed">{move.description_fr}</p>
            </div>
          )}
          {move.description_en && move.description_en !== move.description_fr && (
            <div className={move.description_fr ? "pt-3 border-t border-if-border-lo" : ""}>
              <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-1">Description (EN)</p>
              <p className="text-sm text-if-text-dim leading-relaxed">{move.description_en}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
