"use client";

import { Suspense } from "react";
import Link from "next/link";
import { Clock, Trash2 } from "lucide-react";
import { FusionSelector } from "@/components/fusion/FusionSelector";
import { FusionSprite } from "@/components/fusion/FusionSprite";
import { useHistory } from "@/hooks/useHistory";

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
          title="Effacer l'historique"
        >
          <Trash2 size={11} />
          Effacer
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "thin" }}>
        {entries.slice(0, 10).map((entry) => (
          <Link
            key={`${entry.headId}-${entry.bodyId}`}
            href={`/fusion/${entry.headId}/${entry.bodyId}`}
            className="flex-shrink-0 flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all hover:border-indigo-500/60 group"
            style={{
              background: "#0f1225",
              border: "1px solid #1e2240",
              width: 84,
            }}
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

      <RecentFusions />

      <Suspense>
        <FusionSelector />
      </Suspense>
    </div>
  );
}
