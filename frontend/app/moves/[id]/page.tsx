"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getMove } from "@/lib/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { formatPower, formatAccuracy, formatCategory } from "@/lib/utils";

export default function MoveDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const moveId = parseInt(id, 10);

  const { data: move, isLoading } = useQuery({
    queryKey: ["move", moveId],
    queryFn: () => getMove(moveId),
    staleTime: Infinity,
  });

  if (isLoading) return <PageSkeleton />;
  if (!move) return <NotFound id={moveId} />;

  const catColor =
    move.category === "Physical" ? "#c43030"
    : move.category === "Special" ? "#4a7fd4"
    : "#6b7280";

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <Link
        href="/moves"
        className="inline-flex items-center gap-1 text-sm mb-6 transition-colors"
        style={{ color: "var(--color-if-muted)" }}
      >
        <ChevronLeft size={14} /> Capacités
      </Link>

      <div
        className="rounded-2xl p-5 mb-5"
        style={{
          background: "var(--color-if-card)",
          border: "1px solid var(--color-if-border)",
        }}
      >
        <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--color-if-text)" }}>
              {move.name_fr ?? move.name_en}
            </h1>
            {move.name_fr && (
              <p className="text-sm" style={{ color: "var(--color-if-muted)" }}>{move.name_en}</p>
            )}
          </div>
          <TypeBadge typeName={move.type.name_en} label={move.type.name_fr ?? move.type.name_en} />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: "Catégorie", value: formatCategory(move.category), color: catColor },
            { label: "Puissance",  value: formatPower(move.power), color: "var(--color-if-text-hi)" },
            { label: "Précision",  value: formatAccuracy(move.accuracy), color: "var(--color-if-text-hi)" },
            { label: "PP",         value: String(move.pp), color: "var(--color-if-text-hi)" },
            { label: "Source",     value: move.source === "infinite_fusion" ? "Infinite Fusion" : "Base", color: "var(--color-if-muted)" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-lg px-3 py-2 flex flex-col"
              style={{ background: "var(--color-if-surface)", border: "1px solid var(--color-if-border-lo)" }}
            >
              <span className="text-[10px] uppercase tracking-wide mb-0.5" style={{ color: "var(--color-if-muted)" }}>{label}</span>
              <span className="text-sm font-semibold font-mono" style={{ color }}>{value}</span>
            </div>
          ))}
        </div>

        {/* Descriptions */}
        {move.description_fr && (
          <p className="text-sm mb-2" style={{ color: "var(--color-if-text-dim)" }}>{move.description_fr}</p>
        )}
        {move.description_en && (
          <p className="text-sm" style={{ color: "var(--color-if-muted)", borderTop: "1px solid var(--color-if-border-lo)", paddingTop: "0.5rem", marginTop: "0.5rem" }}>
            {move.description_en}
          </p>
        )}
      </div>

      {/* TM info */}
      {move.tm && (
        <div
          className="rounded-2xl p-5"
          style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
        >
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-if-muted)" }}>
            CT{String(move.tm.number).padStart(2, "0")}
          </h2>
          {move.tm.location_summary && (
            <p className="text-sm mb-3" style={{ color: "var(--color-if-text-dim)" }}>{move.tm.location_summary}</p>
          )}
          {move.tm.locations.length > 0 && (
            <ul className="space-y-1">
              {move.tm.locations.map((loc) => (
                <li key={loc.location_id} className="text-sm flex justify-between gap-4" style={{ color: "var(--color-if-text)" }}>
                  <span>{loc.location_name_fr ?? loc.location_name_en}</span>
                  {loc.notes && <span className="text-xs" style={{ color: "var(--color-if-muted)" }}>{loc.notes}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 animate-pulse">
      <div className="h-4 w-24 bg-if-elevated rounded mb-6" />
      <div className="rounded-2xl p-5 bg-if-card border border-if-border space-y-4">
        <div className="h-8 w-48 bg-if-elevated rounded" />
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 bg-if-elevated rounded-lg" />)}
        </div>
        <div className="h-16 bg-if-elevated rounded" />
      </div>
    </div>
  );
}

function NotFound({ id }: { id: number }) {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p style={{ color: "var(--color-if-muted)" }}>Capacité #{id} introuvable.</p>
      <Link href="/moves" className="mt-4 block transition-colors" style={{ color: "var(--color-if-accent)" }}>
        <ChevronLeft size={14} className="inline" /> Retour aux capacités
      </Link>
    </div>
  );
}
