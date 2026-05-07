"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getAbility } from "@/lib/api";

export default function AbilityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const abilityId = parseInt(id, 10);

  const { data: ability, isLoading } = useQuery({
    queryKey: ["ability", abilityId],
    queryFn: () => getAbility(abilityId),
    staleTime: Infinity,
  });

  if (isLoading) return <PageSkeleton />;
  if (!ability) return <NotFound id={abilityId} />;

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <Link
        href="/abilities"
        className="inline-flex items-center gap-1 text-sm mb-6 transition-colors"
        style={{ color: "var(--color-if-muted)" }}
      >
        <ChevronLeft size={14} /> Talents
      </Link>

      <div
        className="rounded-2xl p-5"
        style={{
          background: "var(--color-if-card)",
          border: "1px solid var(--color-if-border)",
        }}
      >
        <h1 className="text-2xl font-bold mb-0.5" style={{ color: "var(--color-if-text)" }}>
          {ability.name_fr ?? ability.name_en}
        </h1>
        {ability.name_fr && (
          <p className="text-sm mb-4" style={{ color: "var(--color-if-muted)" }}>{ability.name_en}</p>
        )}

        {ability.description_fr && (
          <p className="text-sm mb-2" style={{ color: "var(--color-if-text-dim)" }}>{ability.description_fr}</p>
        )}
        {ability.description_en && (
          <p
            className="text-sm"
            style={{
              color: "var(--color-if-muted)",
              borderTop: "1px solid var(--color-if-border-lo)",
              paddingTop: "0.5rem",
              marginTop: "0.5rem",
            }}
          >
            {ability.description_en}
          </p>
        )}

        {!ability.description_fr && !ability.description_en && (
          <p className="text-sm" style={{ color: "var(--color-if-muted)" }}>Aucune description disponible.</p>
        )}
      </div>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 animate-pulse">
      <div className="h-4 w-24 bg-if-elevated rounded mb-6" />
      <div className="rounded-2xl p-5 bg-if-card border border-if-border space-y-3">
        <div className="h-8 w-48 bg-if-elevated rounded" />
        <div className="h-4 w-32 bg-if-elevated rounded" />
        <div className="h-16 bg-if-elevated rounded" />
      </div>
    </div>
  );
}

function NotFound({ id }: { id: number }) {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <p style={{ color: "var(--color-if-muted)" }}>Talent #{id} introuvable.</p>
      <Link href="/abilities" className="mt-4 block transition-colors" style={{ color: "var(--color-if-accent)" }}>
        <ChevronLeft size={14} className="inline" /> Retour aux talents
      </Link>
    </div>
  );
}
