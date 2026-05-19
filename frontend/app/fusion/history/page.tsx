"use client";

import Link from "next/link";
import { ChevronLeft, Trash2, Clock } from "lucide-react";
import { useHistory } from "@/hooks/useHistory";
import { FusionSprite } from "@/components/fusion/FusionSprite";

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const min  = Math.floor(diff / 60_000);
  const hr   = Math.floor(diff / 3_600_000);
  const day  = Math.floor(diff / 86_400_000);
  if (min < 1)   return "à l'instant";
  if (min < 60)  return `il y a ${min} min`;
  if (hr  < 24)  return `il y a ${hr}h`;
  return `il y a ${day}j`;
}

export default function FusionHistoryPage() {
  const { entries, clearHistory } = useHistory();

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link href="/fusion" className="text-if-muted hover:text-[#e8b84b] transition-colors">
            <ChevronLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-indigo-400" />
            <h1 className="text-xl font-bold text-if-text-hi">Historique des fusions</h1>
          </div>
        </div>

        {entries.length > 0 && (
          <button
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{ background: "rgba(239,68,68,0.1)", border: "1px solid #ef444433", color: "#f87171" }}
          >
            <Trash2 size={12} />
            Effacer
          </button>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="text-center py-16">
          <Clock size={40} className="mx-auto mb-4 text-if-elevated" />
          <p className="text-if-text-xs">Aucune fusion visitée pour l'instant.</p>
          <Link href="/fusion" className="mt-4 block text-sm transition-colors" style={{ color: "#e8b84b" }}>
            Calculer une fusion →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((e) => (
            <Link
              key={`${e.headId}-${e.bodyId}-${e.visitedAt}`}
              href={`/fusion/${e.headId}/${e.bodyId}`}
              className="flex items-center gap-4 px-4 py-3 rounded-xl transition-all"
              style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
              onMouseEnter={(el) => { (el.currentTarget as HTMLElement).style.borderColor = "#6366f166"; }}
              onMouseLeave={(el) => { (el.currentTarget as HTMLElement).style.borderColor = "var(--color-if-border)"; }}
            >
              <FusionSprite headId={e.headId} bodyId={e.bodyId} size={40} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-if-text-hi truncate">
                  {e.headName}/{e.bodyName}
                </p>
                <p className="text-xs" style={{ color: "var(--color-if-text-lo)" }}>
                  #{e.headId} × #{e.bodyId}
                </p>
              </div>
              <span className="text-xs shrink-0" style={{ color: "var(--color-if-border-hi)" }}>
                {timeAgo(e.visitedAt)}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
