"use client";

// Fusion sprite served from the local sprite service via the API proxy.
// Endpoint: GET /api/sprites/{headId}/{bodyId}/image → PNG (200) or 404.
// Falls back to a placeholder div when the sprite doesn't exist.

import { useState } from "react";

export interface FusionSpriteProps {
  headId: number;
  bodyId: number;
  size?: number;
  className?: string;
}

export function FusionSprite({
  headId,
  bodyId,
  size = 128,
  className = "",
}: FusionSpriteProps) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div
        className={className}
        style={{ width: size, height: size }}
        title={`Sprite ${headId}/${bodyId} non disponible`}
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/api/sprites/${headId}/${bodyId}/image`}
      alt={`Fusion ${headId}/${bodyId}`}
      width={size}
      height={size}
      onError={() => setError(true)}
      className={className}
      style={{ imageRendering: "pixelated", objectFit: "contain" }}
    />
  );
}
