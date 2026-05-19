"use client";

import Link from "next/link";
import Image from "next/image";
import { ChevronLeft, Star, Trash2 } from "lucide-react";
import { usePokemonFavorites } from "@/hooks/usePokemonFavorites";
import { basePokemonSprite } from "@/lib/constants";

export default function PokemonFavoritesPage() {
  const { favorites, clearFavorites, toggleFavorite } = usePokemonFavorites();

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link href="/pokedex" className="text-if-muted hover:text-[#e8b84b] transition-colors">
            <ChevronLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <Star size={16} className="text-yellow-400" />
            <h1 className="text-xl font-bold text-if-text-hi">Pokémon favoris</h1>
            {favorites.length > 0 && (
              <span className="text-xs font-mono px-2 py-0.5 rounded-full" style={{ background: "rgba(232,184,75,0.12)", color: "#e8b84b" }}>
                {favorites.length}
              </span>
            )}
          </div>
        </div>

        {favorites.length > 0 && (
          <button
            onClick={clearFavorites}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{ background: "rgba(239,68,68,0.1)", border: "1px solid #ef444433", color: "#f87171" }}
          >
            <Trash2 size={12} />
            Tout effacer
          </button>
        )}
      </div>

      {favorites.length === 0 ? (
        <div className="text-center py-16">
          <Star size={40} className="mx-auto mb-4 text-if-elevated" />
          <p className="text-if-text-xs">Aucun Pokémon en favori pour l'instant.</p>
          <Link href="/pokedex" className="mt-4 block text-sm transition-colors" style={{ color: "#e8b84b" }}>
            Explorer le Pokédex →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {favorites.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-4 px-4 py-3 rounded-xl transition-all group"
              style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#e8b84b44"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--color-if-border)"; }}
            >
              <Link href={`/pokedex/${f.id}`} className="shrink-0">
                <Image
                  src={basePokemonSprite(f.nationalId ?? f.id)}
                  alt={f.nameEn}
                  width={48}
                  height={48}
                  unoptimized
                  className="object-contain"
                />
              </Link>
              <Link href={`/pokedex/${f.id}`} className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-if-text-hi truncate group-hover:text-[#e8b84b] transition-colors">
                  {f.nameFr ?? f.nameEn}
                </p>
                <p className="text-xs" style={{ color: "var(--color-if-text-lo)" }}>
                  {f.nameFr ? f.nameEn + " · " : ""}#{String(f.id).padStart(3, "0")}
                </p>
              </Link>
              <button
                onClick={() => toggleFavorite({ id: f.id, nationalId: f.nationalId ?? null, nameEn: f.nameEn, nameFr: f.nameFr })}
                aria-label="Retirer des favoris"
                className="shrink-0 p-1.5 rounded-lg opacity-50 hover:opacity-100 transition-opacity"
                style={{ color: "#f87171" }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
