"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, Palette } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getCreator, getCreatorSprites } from "@/lib/api";
import type { SpriteOut } from "@/types/api";

export default function CreatorDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const creatorId = parseInt(id, 10);

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

  if (creatorLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 animate-pulse space-y-4">
        <div className="h-8 w-48 rounded bg-[#1e2240]" />
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-lg bg-[#1e2240]" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !creator) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-[rgb(120,120,140)]">Créateur introuvable.</p>
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
        <Link href="/creators" className="text-[rgb(100,100,130)] hover:text-[#e8b84b] transition-colors">
          <ChevronLeft size={20} />
        </Link>
        <div className="flex items-center gap-2">
          <Palette size={18} className="text-indigo-400" />
          <h1 className="text-2xl font-bold text-[rgb(220,220,255)]">{creator.name}</h1>
          <span className="text-sm font-mono" style={{ color: "#4a4f75" }}>
            · {creator.sprite_count} sprite{creator.sprite_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Sprites grid */}
      {spritesLoading ? (
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 animate-pulse">
          {Array.from({ length: 32 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-lg bg-[#1e2240]" />
          ))}
        </div>
      ) : sprites.length === 0 ? (
        <p className="text-center text-sm py-12" style={{ color: "#4a4f75" }}>Aucun sprite trouvé.</p>
      ) : (
        <>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
            {sprites.map((s) => (
              <SpriteCard key={s.id} sprite={s} />
            ))}
          </div>
          <p className="text-xs text-center mt-4" style={{ color: "#3a3f65" }}>
            {sprites.length} sprite{sprites.length !== 1 ? "s" : ""} affichés
          </p>
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
      style={{ background: "#090c1a", border: "1px solid #1e2240" }}
      title={`${sprite.head_id}/${sprite.body_id}`}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#6366f166"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#1e2240"; }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/sprites/${sprite.head_id}/${sprite.body_id}/image`}
        alt={`Fusion ${sprite.head_id}/${sprite.body_id}`}
        width={64}
        height={64}
        style={{ imageRendering: "pixelated", objectFit: "contain" }}
        className="w-full h-full p-1 group-hover:scale-110 transition-transform duration-150"
        onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0"; }}
      />
      <span className="absolute bottom-0 left-0 right-0 text-center text-[9px] leading-tight py-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ color: "#818cf8", background: "rgba(9,12,26,0.85)" }}>
        {sprite.head_id}/{sprite.body_id}
      </span>
    </Link>
  );
}
