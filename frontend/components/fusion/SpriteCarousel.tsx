"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CreatorBadge } from "@/components/fusion/CreatorModal";
import type { SpriteOut } from "@/types/api";

interface SpriteCarouselProps {
  headId: number;
  bodyId: number;
  sprites: SpriteOut[];
  size?: number;
}

export function SpriteCarousel({
  headId,
  bodyId,
  sprites,
  size = 128,
}: SpriteCarouselProps) {
  const [idx, setIdx] = useState(0);

  const sprite = sprites[idx];
  const total  = sprites.length;
  const hasMany = total > 1;

  const prev = () => setIdx((i) => (i - 1 + total) % total);
  const next = () => setIdx((i) => (i + 1) % total);

  const src = sprite
    ? `/api/sprites/${headId}/${bodyId}/image?variant_id=${sprite.id}`
    : `/api/sprites/${headId}/${bodyId}/image`;

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Image + nav arrows */}
      <div className="relative group">
        <div
          className="flex items-center justify-center rounded-xl shrink-0"
          style={{
            width: size,
            height: size,
            background: "#090c1a",
            border: "1px solid #1e2240",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={sprite?.id ?? "default"}
            src={src}
            alt={`Fusion ${headId}/${bodyId} variant ${idx + 1}`}
            width={size}
            height={size}
            style={{ imageRendering: "pixelated", objectFit: "contain" }}
          />
        </div>

        {hasMany && (
          <>
            <button
              onClick={prev}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: "#1e2240", border: "1px solid #2d3260" }}
              aria-label="Sprite précédent"
            >
              <ChevronLeft size={12} className="text-indigo-300" />
            </button>
            <button
              onClick={next}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: "#1e2240", border: "1px solid #2d3260" }}
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
        <p className="text-[10px]" style={{ color: "#4a4f75" }}>
          {idx + 1} / {total}
        </p>
      )}

      {sprite && sprite.creators.length > 0 ? (
        <p className="text-[10px] text-center leading-tight" style={{ color: "#6b7199" }}>
          par{" "}
          {sprite.creators.map((c, i) => (
            <span key={c}>
              {i > 0 && ", "}
              <CreatorBadge name={c} />
            </span>
          ))}
        </p>
      ) : (
        <p className="text-[10px] italic" style={{ color: "#3a3f65" }}>
          Auto-généré
        </p>
      )}
    </div>
  );
}
