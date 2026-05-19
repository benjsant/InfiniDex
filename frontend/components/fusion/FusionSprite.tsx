"use client";

// Fusion sprite served from the local sprite service via the API proxy.
// Endpoint: GET /api/sprites/{headId}/{bodyId}/image → PNG (200) or 404.
// Falls back to side-by-side PokeAPI sprites (via national dex id lookup).

import { useState } from "react";
import { usePokemonIdMap } from "@/hooks/usePokemon";

export interface FusionSpriteProps {
  headId: number;
  bodyId: number;
  size?: number;
  className?: string;
}

function PokeApiSprite({ id, size, label }: { id: number; size: number; label: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png`}
      alt={label}
      width={size}
      height={size}
      style={{ imageRendering: "pixelated", objectFit: "contain", opacity: 0.75 }}
    />
  );
}

export function FusionSprite({
  headId,
  bodyId,
  size = 128,
  className = "",
}: FusionSpriteProps) {
  const [error, setError] = useState(false);
  const idMap = usePokemonIdMap();

  if (error) {
    const half = Math.round(size * 0.55);
    const headNat = idMap.get(headId) ?? headId;
    const bodyNat = idMap.get(bodyId) ?? bodyId;
    return (
      <div
        className={`flex items-center justify-center gap-0.5 ${className}`}
        style={{ width: size, height: size }}
        title={`Sprite ${headId}/${bodyId} — aperçu de base`}
      >
        <PokeApiSprite id={headNat} size={half} label={`Pokémon tête #${headId}`} />
        <PokeApiSprite id={bodyNat} size={half} label={`Pokémon corps #${bodyId}`} />
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/api/sprites/${headId}/${bodyId}/image`}
      alt={`Fusion ${headId}/${bodyId}`}
      width={size}
      height={size}
      loading="lazy"
      onError={() => setError(true)}
      className={className}
      style={{ imageRendering: "pixelated", objectFit: "contain" }}
    />
  );
}
