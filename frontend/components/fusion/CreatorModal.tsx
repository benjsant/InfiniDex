"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { X, Palette } from "lucide-react";
import { searchCreators, getCreatorSprites } from "@/lib/api";
import type { SpriteOut } from "@/types/api";

interface CreatorModalProps {
  name: string;
  onClose: () => void;
}

export function CreatorModal({ name, onClose }: CreatorModalProps) {
  // Resolve name → id
  const { data: creators = [] } = useQuery({
    queryKey: ["creator-search", name],
    queryFn: () => searchCreators(name),
    staleTime: Infinity,
  });

  const creator = creators.find(
    (c) => c.name.toLowerCase() === name.toLowerCase()
  ) ?? creators[0];

  const { data: sprites = [], isLoading } = useQuery<SpriteOut[]>({
    queryKey: ["creator-sprites", creator?.id],
    queryFn: () => getCreatorSprites(creator!.id),
    enabled: !!creator,
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
      <div className="relative w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl bg-if-surface border border-if-border-mid shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-if-border-lo shrink-0">
          <Palette size={16} className="text-indigo-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-if-text-hi truncate">{name}</p>
            {creator && (
              <p className="text-xs text-if-muted">
                {creator.sprite_count} sprite{creator.sprite_count > 1 ? "s" : ""} dans la base
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg text-if-muted hover:text-white hover:bg-if-border transition-colors"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Grid */}
        <div className="overflow-y-auto p-4">
          {isLoading || !creator ? (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {Array.from({ length: 24 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-lg bg-if-elevated animate-pulse" />
              ))}
            </div>
          ) : sprites.length === 0 ? (
            <p className="text-center text-sm text-if-muted py-8">Aucun sprite trouvé.</p>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {sprites.map((s) => (
                <Link
                  key={s.id}
                  href={`/fusion/${s.head_id}/${s.body_id}`}
                  onClick={onClose}
                  className="group relative aspect-square flex items-center justify-center rounded-lg bg-if-deep border border-if-border-lo hover:border-indigo-500 transition-colors overflow-hidden"
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
                  <span className="absolute bottom-0 left-0 right-0 text-center text-[9px] text-if-muted group-hover:text-indigo-300 pb-0.5 bg-if-deep/80 leading-tight">
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

// Small inline button to trigger the modal
export function CreatorBadge({ name }: { name: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
        className="text-[10px] text-indigo-400 hover:text-indigo-300 hover:underline transition-colors"
      >
        {name}
      </button>
      {open && <CreatorModal name={name} onClose={() => setOpen(false)} />}
    </>
  );
}
