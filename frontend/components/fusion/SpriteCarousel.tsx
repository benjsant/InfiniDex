"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CreatorBadge } from "@/components/fusion/CreatorModal";
import { usePokemonIdMap } from "@/hooks/usePokemon";
import type { SpriteOut } from "@/types/api";

interface SpriteCarouselProps {
  headId: number;
  bodyId: number;
  sprites: SpriteOut[];
  size?: number;
  loading?: boolean;
}

export function SpriteCarousel({
  headId,
  bodyId,
  sprites,
  size = 128,
  loading = false,
}: SpriteCarouselProps) {
  const idMap = usePokemonIdMap();
  const [idx, setIdx] = useState(0);
  const [imgError, setImgError] = useState(false);

  const sprite = sprites[idx];
  const total  = sprites.length;
  const hasMany = total > 1;

  const prev = () => { setIdx((i) => (i - 1 + total) % total); setImgError(false); };
  const next = () => { setIdx((i) => (i + 1) % total); setImgError(false); };

  const src = sprite
    ? `/api/sprites/${headId}/${bodyId}/image?variant_id=${sprite.id}`
    : `/api/sprites/${headId}/${bodyId}/image`;

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div
          className="rounded-xl animate-pulse shrink-0"
          style={{ width: size, height: size, background: "var(--color-if-border)" }}
        />
        <div className="h-2.5 w-16 rounded bg-if-border animate-pulse" />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Image + nav arrows */}
      <div className="relative group">
        <div
          className="flex items-center justify-center rounded-xl shrink-0"
          style={{
            width: size,
            height: size,
            background: "var(--color-if-bg)",
            border: "1px solid var(--color-if-border)",
          }}
        >
          {imgError ? (
            <div className="flex items-center justify-center gap-0.5" title="Aperçu de base — pas de sprite custom">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${idMap.get(headId) ?? headId}.png`}
                alt={`Sprite Pokémon tête #${headId}`}
                width={Math.round(size * 0.55)}
                height={Math.round(size * 0.55)}
                style={{ imageRendering: "pixelated", objectFit: "contain", opacity: 0.75 }}
              />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${idMap.get(bodyId) ?? bodyId}.png`}
                alt={`Sprite Pokémon corps #${bodyId}`}
                width={Math.round(size * 0.55)}
                height={Math.round(size * 0.55)}
                style={{ imageRendering: "pixelated", objectFit: "contain", opacity: 0.75 }}
              />
            </div>
          ) : (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              key={sprite?.id ?? "default"}
              src={src}
              alt={`Fusion ${headId}/${bodyId} variant ${idx + 1}`}
              width={size}
              height={size}
              loading="lazy"
              onError={() => setImgError(true)}
              style={{ imageRendering: "pixelated", objectFit: "contain" }}
            />
          )}
        </div>

        {hasMany && (
          <>
            <button
              onClick={prev}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: "var(--color-if-border)", border: "1px solid var(--color-if-border-hi)" }}
              aria-label="Sprite précédent"
            >
              <ChevronLeft size={12} className="text-indigo-300" />
            </button>
            <button
              onClick={next}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: "var(--color-if-border)", border: "1px solid var(--color-if-border-hi)" }}
              aria-label="Sprite suivant"
            >
              <ChevronRight size={12} className="text-indigo-300" />
            </button>
          </>
        )}
      </div>

      {/* Dots */}
      {hasMany && (
        <div className="flex gap-1">
          {sprites.map((_, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className="w-1.5 h-1.5 rounded-full transition-colors"
              style={{ background: i === idx ? "#6366f1" : "#2d3260" }}
              aria-label={`Sprite ${i + 1}`}
            />
          ))}
        </div>
      )}

      {/* Counter + creator */}
      {hasMany && (
        <p className="text-[10px]" style={{ color: "var(--color-if-text-lo)" }}>
          {idx + 1} / {total}
        </p>
      )}

      {imgError ? (
        <p className="text-[10px] italic" style={{ color: "var(--color-if-border-hi)" }}>
          Pas de sprite custom
        </p>
      ) : sprite && sprite.creators.length > 0 ? (
        <p className="text-[10px] text-center leading-tight" style={{ color: "var(--color-if-muted)" }}>
          par{" "}
          {sprite.creators.map((c, i) => (
            <span key={c}>
              {i > 0 && ", "}
              <CreatorBadge name={c} />
            </span>
          ))}
        </p>
      ) : (
        <p className="text-[10px] italic" style={{ color: "var(--color-if-border-hi)" }}>
          Auto-généré
        </p>
      )}
    </div>
  );
}
