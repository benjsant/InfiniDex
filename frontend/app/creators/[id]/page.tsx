"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Users } from "lucide-react";
import { getCreator, getCreatorSprites } from "@/lib/api";
import type { SpriteOut } from "@/types/api";

export default function CreatorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const creatorId = Number(id);

  const { data: creator, isLoading: loadingCreator } = useQuery({
    queryKey: ["creator", creatorId],
    queryFn: () => getCreator(creatorId),
    enabled: !isNaN(creatorId),
    staleTime: Infinity,
  });

  const { data: sprites = [], isLoading: loadingSprites } = useQuery<SpriteOut[]>({
    queryKey: ["creator-sprites", creatorId],
    queryFn: () => getCreatorSprites(creatorId),
    enabled: !isNaN(creatorId),
    staleTime: Infinity,
  });

  const isLoading = loadingCreator || loadingSprites;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Back + header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/creators"
          className="p-2 rounded-lg text-if-muted hover:text-white hover:bg-if-input transition-colors"
          aria-label="Retour"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="w-10 h-10 rounded-full bg-indigo-900/40 border border-indigo-700/30 flex items-center justify-center shrink-0">
          <Users size={18} className="text-indigo-400" />
        </div>
        <div>
          {loadingCreator ? (
            <div className="h-6 w-40 rounded bg-if-input animate-pulse" />
          ) : (
            <h1 className="text-xl font-bold text-if-text-hi">{creator?.name ?? "Créateur"}</h1>
          )}
          {creator && (
            <p className="text-xs text-if-muted mt-0.5">
              {creator.sprite_count.toLocaleString()} sprite{creator.sprite_count > 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {/* Sprite grid */}
      {isLoading ? (
        <SkeletonGrid />
      ) : sprites.length === 0 ? (
        <p className="text-center text-if-text-xs py-12">Aucun sprite trouvé.</p>
      ) : (
        <>
          <p className="text-sm text-if-text-xs mb-4">
            {sprites.length.toLocaleString()} sprite{sprites.length > 1 ? "s" : ""}
          </p>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 xl:grid-cols-12 gap-2">
            {sprites.map((s) => (
              <SpriteCard key={s.id} sprite={s} />
            ))}
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
      className="group relative aspect-square flex items-center justify-center rounded-lg bg-if-deep border border-if-border-lo hover:border-indigo-500 transition-colors overflow-hidden"
      title={`Fusion ${sprite.head_id}/${sprite.body_id}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/sprites/${sprite.head_id}/${sprite.body_id}/image`}
        alt={`${sprite.head_id}/${sprite.body_id}`}
        width={64}
        height={64}
        style={{ imageRendering: "pixelated", objectFit: "contain" }}
        className="w-full h-full p-1 group-hover:scale-110 transition-transform duration-150"
        onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0"; }}
      />
      <span className="absolute bottom-0 left-0 right-0 text-center text-[8px] text-if-muted group-hover:text-indigo-300 pb-0.5 bg-if-deep/80 leading-tight">
        {sprite.head_id}/{sprite.body_id}
      </span>
    </Link>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 xl:grid-cols-12 gap-2">
      {Array.from({ length: 48 }).map((_, i) => (
        <div key={i} className="aspect-square rounded-lg bg-if-deep border border-if-border-lo animate-pulse" />
      ))}
    </div>
  );
}
