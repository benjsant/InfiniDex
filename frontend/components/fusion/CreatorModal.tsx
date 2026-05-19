"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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

  const dialogRef = useRef<HTMLDivElement>(null);

  // Close on Escape + focus trap
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])'
        )
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last  = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last)  { e.preventDefault(); first.focus(); }
      }
    },
    [onClose]
  );
  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    // Move focus into the modal on open
    setTimeout(() => dialogRef.current?.querySelector<HTMLElement>("button,a")?.focus(), 50);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  const titleId = `creator-modal-title-${name.replace(/\s+/g, "-")}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl bg-if-card border border-if-border-mid shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-if-input shrink-0">
          <Palette size={16} className="text-indigo-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p id={titleId} className="font-semibold text-if-text-hi truncate">{name}</p>
            {resolvedCount != null && (
              <p className="text-xs text-if-muted">
                {resolvedCount} sprite{resolvedCount > 1 ? "s" : ""} dans la base
              </p>
            )}
          </div>
          {detailHref && (
            <Link
              href={detailHref}
              onClick={onClose}
              className="shrink-0 p-1.5 rounded-lg transition-colors hover:bg-if-input"
              style={{ color: "var(--color-if-muted)" }}
              title="Page complète"
            >
              <ExternalLink size={14} />
            </Link>
          )}
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg text-if-muted hover:text-white hover:bg-if-input transition-colors"
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
                  className="group relative aspect-square flex items-center justify-center rounded-lg bg-if-surface border border-if-input hover:border-indigo-500 transition-colors overflow-hidden"
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
                  <span className="absolute bottom-0 left-0 right-0 text-center text-[9px] text-if-muted group-hover:text-indigo-300 pb-0.5 bg-if-surface/80 leading-tight">
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
