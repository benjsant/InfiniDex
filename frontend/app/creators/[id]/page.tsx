"use client";

import { use, useState, useMemo } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Palette } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getCreator, getCreatorSprites } from "@/lib/api";
import type { SpriteOut } from "@/types/api";

const PAGE_SIZE = 48;

export default function CreatorDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const creatorId = parseInt(id, 10);
  const [page, setPage] = useState(1);

  const { data: creator, isLoading: creatorLoading, error } = useQuery({
    queryKey: ["creator", creatorId],
    queryFn: () => getCreator(creatorId),
    staleTime: Infinity,
  });

  const { data: sprites = [], isLoading: spritesLoading } = useQuery<SpriteOut[]>({
    queryKey: ["creator-sprites", creatorId],
    queryFn: () => getCreatorSprites(creatorId),
    staleTime: Infinity,
    enabled: !creatorLoading && !error,
  });

  const totalPages = Math.ceil(sprites.length / PAGE_SIZE);
  const pageSprites = useMemo(
    () => sprites.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [sprites, page],
  );

  if (creatorLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 animate-pulse space-y-4">
        <div className="h-8 w-48 rounded bg-if-border" />
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-lg bg-if-border" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !creator) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-if-text-xs">Créateur introuvable.</p>
        <Link href="/creators" className="mt-4 block text-sm transition-colors" style={{ color: "#e8b84b" }}>
          <ChevronLeft size={14} className="inline" /> Retour aux créateurs
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/creators" className="text-if-muted hover:text-[#e8b84b] transition-colors">
          <ChevronLeft size={20} />
        </Link>
        <div className="flex items-center gap-2">
          <Palette size={18} className="text-indigo-400" />
          <h1 className="text-2xl font-bold text-if-text-hi">{creator.name}</h1>
          <span className="text-sm font-mono" style={{ color: "var(--color-if-text-lo)" }}>
            · {creator.sprite_count} sprite{creator.sprite_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Sprites grid */}
      {spritesLoading ? (
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 animate-pulse">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <div key={i} className="aspect-square rounded-lg bg-if-border" />
          ))}
        </div>
      ) : sprites.length === 0 ? (
        <p className="text-center text-sm py-12" style={{ color: "var(--color-if-text-lo)" }}>Aucun sprite trouvé.</p>
      ) : (
        <>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
            {pageSprites.map((s) => (
              <SpriteCard key={s.id} sprite={s} />
            ))}
          </div>

          <div className="flex items-center justify-between mt-5">
            <p className="text-xs" style={{ color: "var(--color-if-border-hi)" }}>
              {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, sprites.length)} / {sprites.length} sprites
            </p>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded-lg text-xs transition-all disabled:opacity-30"
                  style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-muted)" }}
                >
                  <ChevronLeft size={14} className="inline" /> Préc.
                </button>
                <span className="text-xs" style={{ color: "var(--color-if-text-lo)" }}>
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 rounded-lg text-xs transition-all disabled:opacity-30"
                  style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-muted)" }}
                >
                  Suiv. <ChevronRight size={14} className="inline" />
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SpriteCard({ sprite }: { sprite: SpriteOut }) {
  return (
    <Link
      href={`/fusion/${sprite.head_id}/${sprite.body_id}`}
      className="group relative aspect-square flex items-center justify-center rounded-lg transition-all overflow-hidden"
      style={{ background: "var(--color-if-bg)", border: "1px solid var(--color-if-border)" }}
      title={`${sprite.head_id}/${sprite.body_id}`}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#6366f166"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--color-if-border)"; }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/sprites/${sprite.head_id}/${sprite.body_id}/image`}
        alt={`Fusion ${sprite.head_id}/${sprite.body_id}`}
        width={64}
        height={64}
        style={{ imageRendering: "pixelated", objectFit: "contain" }}
        className="w-full h-full p-1 group-hover:scale-110 transition-transform duration-150"
        loading="lazy"
        onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0"; }}
      />
      <span
        className="absolute bottom-0 left-0 right-0 text-center text-[9px] leading-tight py-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ color: "#818cf8", background: "rgba(9,12,26,0.85)" }}
      >
        {sprite.head_id}/{sprite.body_id}
      </span>
    </Link>
  );
}
