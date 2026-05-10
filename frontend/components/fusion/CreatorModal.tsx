"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { X, Palette, ExternalLink } from "lucide-react";
import { searchCreators, getCreatorSprites } from "@/lib/api";
import type { SpriteOut } from "@/types/api";

interface CreatorModalProps {
  name: string;
  creatorId?: number;
  spriteCount?: number;
  onClose: () => void;
  detailHref?: string;
}

export function CreatorModal({ name, creatorId, spriteCount, onClose, detailHref }: CreatorModalProps) {
  // If id is provided directly (from gallery page), skip the search round-trip
  const { data: creators = [] } = useQuery({
    queryKey: ["creator-search", name],
    queryFn: () => searchCreators(name),
    staleTime: Infinity,
    enabled: creatorId == null,
  });

  const resolvedId = creatorId ?? creators.find(
    (c) => c.name.toLowerCase() === name.toLowerCase()
  )?.id ?? creators[0]?.id;

  const resolvedCount = spriteCount ?? creators.find(
    (c) => c.name.toLowerCase() === name.toLowerCase()
  )?.sprite_count ?? creators[0]?.sprite_count;

  const { data: sprites = [], isLoading } = useQuery<SpriteOut[]>({
    queryKey: ["creator-sprites", resolvedId],
    queryFn: () => getCreatorSprites(resolvedId!),
    enabled: resolvedId != null,
    staleTime: Infinity,
  });

  // Close on Escape
  const handleKey = useCallback(
    (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); },
    [onClose]
  );
  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl bg-[rgb(18,18,26)] border border-[rgb(50,50,70)] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[rgb(35,35,50)] shrink-0">
          <Palette size={16} className="text-indigo-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-[rgb(220,220,255)] truncate">{name}</p>
            {resolvedCount != null && (
              <p className="text-xs text-[rgb(100,100,130)]">
                {resolvedCount} sprite{resolvedCount > 1 ? "s" : ""} dans la base
              </p>
            )}
          </div>
          {detailHref && (
            <Link
              href={detailHref}
              onClick={onClose}
              className="shrink-0 p-1.5 rounded-lg transition-colors hover:bg-[rgb(40,40,55)]"
              style={{ color: "#6b7199" }}
              title="Page complète"
            >
              <ExternalLink size={14} />
            </Link>
          )}
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg text-[rgb(100,100,130)] hover:text-white hover:bg-[rgb(40,40,55)] transition-colors"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Grid */}
        <div className="overflow-y-auto p-4">
          {isLoading || resolvedId == null ? (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {Array.from({ length: 24 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-lg bg-[rgb(25,25,35)] animate-pulse" />
              ))}
            </div>
          ) : sprites.length === 0 ? (
            <p className="text-center text-sm text-[rgb(100,100,130)] py-8">Aucun sprite trouvé.</p>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {sprites.map((s) => (
                <Link
                  key={s.id}
                  href={`/fusion/${s.head_id}/${s.body_id}`}
                  onClick={onClose}
                  className="group relative aspect-square flex items-center justify-center rounded-lg bg-[rgb(15,15,22)] border border-[rgb(35,35,50)] hover:border-indigo-500 transition-colors overflow-hidden"
                  title={`${s.head_id}/${s.body_id}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/api/sprites/${s.head_id}/${s.body_id}/image`}
                    alt={`Fusion ${s.head_id}/${s.body_id}`}
                    width={64}
                    height={64}
                    style={{ imageRendering: "pixelated", objectFit: "contain" }}
                    className="w-full h-full p-1 group-hover:scale-110 transition-transform duration-150"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.opacity = "0";
                    }}
                  />
                  <span className="absolute bottom-0 left-0 right-0 text-center text-[9px] text-[rgb(80,80,100)] group-hover:text-indigo-300 pb-0.5 bg-[rgb(15,15,22)]/80 leading-tight">
                    {s.head_id}/{s.body_id}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Small inline button — opens modal for quick preview; right-click / long-press links to detail page
export function CreatorBadge({ name, creatorId }: { name: string; creatorId?: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
        className="text-[10px] text-indigo-400 hover:text-indigo-300 hover:underline transition-colors"
        title={creatorId ? `Voir les sprites de ${name}` : name}
      >
        {name}
      </button>
      {open && (
        <CreatorModal
          name={name}
          creatorId={creatorId}
          onClose={() => setOpen(false)}
          detailHref={creatorId ? `/creators/${creatorId}` : undefined}
        />
      )}
    </>
  );
}
