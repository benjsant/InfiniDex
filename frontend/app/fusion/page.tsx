"use client";

import { Suspense } from "react";
import Link from "next/link";
import { Clock, Trash2, Star, GitCompare, Download, Sparkles } from "lucide-react";
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
      style={{ background: "var(--color-if-surface)", border: "1px solid var(--color-if-border)", width: 84 }}
    >
      <div
        className="flex items-center justify-center rounded-lg overflow-hidden"
        style={{ width: 56, height: 56, background: "var(--color-if-bg)" }}
      >
        <FusionSprite headId={entry.headId} bodyId={entry.bodyId} size={56} />
      </div>
      <span
        className="text-[10px] text-center leading-tight font-medium group-hover:text-indigo-300 transition-colors line-clamp-2"
        style={{ color: "var(--color-if-text-xs)" }}
      >
        {entry.headName}/{entry.bodyName}
      </span>
    </Link>
  );
}

function exportFavoritesJson(favorites: FusionFavorite[]) {
  const data = favorites.map((f) => ({
    fusion: `${f.headName}/${f.bodyName}`,
    headId: f.headId,
    bodyId: f.bodyId,
    url: `/fusion/${f.headId}/${f.bodyId}`,
  }));
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "infinidex-favoris.json";
  a.click();
  URL.revokeObjectURL(url);
}

function FavoritesSection() {
  const { favorites, clearFavorites } = useFavorites();
  if (favorites.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "#e8b84b" }}>
          <Star size={12} fill="currentColor" />
          Favoris ({favorites.length})
        </span>
        <div className="flex items-center gap-3">
          <button
            onClick={() => exportFavoritesJson(favorites)}
            className="flex items-center gap-1 text-xs transition-colors hover:text-[#e8b84b]"
            style={{ color: "var(--color-if-muted)" }}
            title="Exporter en JSON"
          >
            <Download size={11} />
            Exporter
          </button>
          <button
            onClick={clearFavorites}
            className="flex items-center gap-1 text-xs transition-colors hover:text-red-400"
            style={{ color: "var(--color-if-muted)" }}
          >
            <Trash2 size={11} />
            Effacer
          </button>
        </div>
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
            <span key={i} className="text-xs italic" style={{ color: "var(--color-if-border-hi)" }}>
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
          style={{ color: "var(--color-if-muted)" }}
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
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--color-if-muted)" }}>
          <Clock size={12} />
          Récemment consultées
        </span>
        <div className="flex items-center gap-3">
          <Link
            href="/fusion/history"
            className="text-xs transition-colors hover:text-indigo-300"
            style={{ color: "var(--color-if-text-lo)" }}
          >
            Voir tout →
          </Link>
          <button
            onClick={clearHistory}
            className="flex items-center gap-1 text-xs transition-colors hover:text-red-400"
            style={{ color: "var(--color-if-muted)" }}
          >
            <Trash2 size={11} />
            Effacer
          </button>
        </div>
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
      <div className="flex items-start justify-between mb-2">
        <h1 className="text-2xl font-bold text-if-text-hi">
          Calculateur de Fusion
        </h1>
        <Link
          href="/fusion/top"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
          style={{ background: "rgba(232,184,75,0.1)", border: "1px solid rgba(232,184,75,0.25)", color: "#e8b84b" }}
        >
          <Sparkles size={12} /> Galerie
        </Link>
      </div>
      <p className="text-sm text-if-text-xs mb-8">
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
