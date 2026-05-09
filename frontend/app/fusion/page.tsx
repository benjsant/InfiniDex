"use client";

import { Suspense } from "react";
import Link from "next/link";
import { Clock, Trash2, Star, GitCompare } from "lucide-react";
import { FusionSelector } from "@/components/fusion/FusionSelector";
import { FusionSprite } from "@/components/fusion/FusionSprite";
import { useHistory } from "@/hooks/useHistory";
import { useFavorites } from "@/hooks/useFavorites";
import { useComparison } from "@/hooks/useComparison";
import type { FusionFavorite } from "@/hooks/useFavorites";
import type { FusionHistoryEntry } from "@/hooks/useHistory";

type FusionCardEntry = {
  headId: number;
  bodyId: number;
  headName: string;
  bodyName: string;
};

function FusionMiniCard({ entry }: { entry: FusionCardEntry }) {
  return (
    <Link
      href={`/fusion/${entry.headId}/${entry.bodyId}`}
      className="flex-shrink-0 flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all hover:border-indigo-500/60 group"
      style={{ background: "#0f1225", border: "1px solid #1e2240", width: 84 }}
    >
      <div
        className="flex items-center justify-center rounded-lg overflow-hidden"
        style={{ width: 56, height: 56, background: "#090c1a" }}
      >
        <FusionSprite headId={entry.headId} bodyId={entry.bodyId} size={56} />
      </div>
      <span
        className="text-[10px] text-center leading-tight font-medium group-hover:text-indigo-300 transition-colors line-clamp-2"
        style={{ color: "#9aa0c0" }}
      >
        {entry.headName}/{entry.bodyName}
      </span>
    </Link>
  );
}

function FavoritesSection() {
  const { favorites, clearFavorites } = useFavorites();
  if (favorites.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "#e8b84b" }}>
          <Star size={12} fill="currentColor" />
          Favoris
        </span>
        <button
          onClick={clearFavorites}
          className="flex items-center gap-1 text-xs transition-colors hover:text-red-400"
          style={{ color: "#6b7199" }}
        >
          <Trash2 size={11} />
          Effacer
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "thin" }}>
        {favorites.map((f: FusionFavorite) => (
          <FusionMiniCard key={`${f.headId}-${f.bodyId}`} entry={f} />
        ))}
      </div>
    </div>
  );
}

function ComparisonBanner() {
  const { slots, clearComparison, canCompare } = useComparison();
  const filled = slots.filter(Boolean);
  if (filled.length === 0) return null;

  return (
    <div
      className="mb-6 p-3 rounded-xl flex items-center gap-3 flex-wrap"
      style={{ background: "rgba(99,102,241,0.08)", border: "1px solid #6366f133" }}
    >
      <GitCompare size={14} className="text-indigo-400 shrink-0" />
      <div className="flex items-center gap-2 flex-1 flex-wrap">
        {slots.map((s, i) =>
          s ? (
            <span key={i} className="text-xs font-medium" style={{ color: "#818cf8" }}>
              {s.headName}/{s.bodyName}
            </span>
          ) : (
            <span key={i} className="text-xs italic" style={{ color: "#3d4170" }}>
              — sélectionne une fusion
            </span>
          ),
        )}
      </div>
      <div className="flex items-center gap-2">
        {canCompare && (
          <Link
            href="/fusion/compare"
            className="text-xs px-3 py-1 rounded-lg font-medium transition-all bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            Comparer →
          </Link>
        )}
        <button
          onClick={clearComparison}
          className="text-xs transition-colors hover:text-red-400"
          style={{ color: "#6b7199" }}
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

function RecentFusions() {
  const { entries, clearHistory } = useHistory();
  if (entries.length === 0) return null;

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "#6b7199" }}>
          <Clock size={12} />
          Récemment consultées
        </span>
        <button
          onClick={clearHistory}
          className="flex items-center gap-1 text-xs transition-colors hover:text-red-400"
          style={{ color: "#6b7199" }}
        >
          <Trash2 size={11} />
          Effacer
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "thin" }}>
        {entries.slice(0, 10).map((entry: FusionHistoryEntry) => (
          <FusionMiniCard key={`${entry.headId}-${entry.bodyId}`} entry={entry} />
        ))}
      </div>
    </div>
  );
}

export default function FusionPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2 text-[rgb(220,220,255)]">
        Calculateur de Fusion
      </h1>
      <p className="text-sm text-[rgb(120,120,140)] mb-8">
        Sélectionne la tête et le corps pour calculer les stats, types et voir le sprite de la fusion.
      </p>

      <FavoritesSection />
      <ComparisonBanner />
      <RecentFusions />

      <Suspense>
        <FusionSelector />
      </Suspense>
    </div>
  );
}
