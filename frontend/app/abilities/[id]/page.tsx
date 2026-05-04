"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Star, Sparkles } from "lucide-react";
import { getAbility } from "@/lib/api";

export default function AbilityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const abilityId = Number(id);

  const { data: ability, isLoading, isError } = useQuery({
    queryKey: ["ability", abilityId],
    queryFn: () => getAbility(abilityId),
    enabled: !isNaN(abilityId),
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

  if (isError || !ability) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <p className="text-if-muted">Talent introuvable.</p>
        <Link href="/abilities" className="mt-4 inline-flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300">
          <ArrowLeft size={14} /> Retour aux talents
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <Link
        href="/abilities"
        className="inline-flex items-center gap-1.5 text-sm text-if-muted hover:text-if-text transition-colors mb-6"
      >
        <ArrowLeft size={14} />
        Talents
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 shrink-0">
          <Star size={24} className="text-if-accent" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-3xl font-bold text-if-text-hi">
              {ability.name_fr ?? ability.name_en}
            </h1>
            {ability.if_modified && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-if-accent/10 border border-if-accent/30 text-if-accent">
                <Sparkles size={10} />
                Modifié IF
              </span>
            )}
          </div>
          {ability.name_fr && (
            <p className="text-if-muted text-sm mt-0.5">{ability.name_en}</p>
          )}
        </div>
      </div>

      {/* Descriptions */}
      <div className="if-panel p-4 space-y-4">
        {ability.description_fr && (
          <div>
            <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-1.5">Description (FR)</p>
            <p className="text-sm text-if-text leading-relaxed">{ability.description_fr}</p>
          </div>
        )}
        {ability.description_en && (
          <div className={ability.description_fr ? "pt-4 border-t border-if-border-lo" : ""}>
            <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-1.5">Description (EN)</p>
            <p className="text-sm text-if-text-dim leading-relaxed">{ability.description_en}</p>
          </div>
        )}
      </div>

      {/* IF Notes */}
      {ability.if_modified && ability.if_notes && (
        <div className="mt-4 p-4 rounded-xl" style={{ background: "rgba(232,184,75,0.08)", border: "1px solid rgba(232,184,75,0.25)" }}>
          <p className="text-xs font-semibold text-if-accent uppercase tracking-wider mb-1.5">Notes Infinite Fusion</p>
          <p className="text-sm text-if-text-dim leading-relaxed">{ability.if_notes}</p>
        </div>
      )}
    </div>
  );
}
