import Link from "next/link";
import Image from "next/image";
import type { PokemonListItem } from "@/types/api";
import { TypeBadge } from "./TypeBadge";
import { basePokemonSprite, typeColor } from "@/lib/constants";
import { primaryType, secondaryType } from "@/lib/utils";

interface PokemonCardProps {
  pokemon: PokemonListItem;
}

export function PokemonCard({ pokemon }: PokemonCardProps) {
  const spriteUrl = basePokemonSprite(pokemon.national_id ?? pokemon.id);
  const t1 = primaryType(pokemon.types);
  const t2 = secondaryType(pokemon.types);
  const color1 = t1 ? typeColor(t1.name_en) : "#6366f1";

  return (
    <Link
      href={`/pokedex/${pokemon.id}`}
      className="group relative flex flex-col items-center gap-2 pt-3 pb-3 px-2 rounded-xl transition-all duration-200 overflow-hidden"
      style={{
        background: `linear-gradient(160deg, var(--color-if-card) 60%, ${color1}18)`,
        border: `1px solid var(--color-if-border)`,
        boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = `${color1}90`;
        (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 20px ${color1}30`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "#1e2240";
        (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 8px rgba(0,0,0,0.4)";
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl"
        style={{ background: `linear-gradient(90deg, transparent, ${color1}, transparent)` }}
      />

      {/* Sprite with radial glow behind */}
      <div className="relative w-20 h-20 flex items-center justify-center">
        <div
          className="absolute inset-0 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity"
          style={{ background: color1 }}
        />
        <Image
          src={spriteUrl}
          alt={pokemon.name_en}
          width={80}
          height={80}
          unoptimized
          className="relative object-contain group-hover:scale-110 transition-transform duration-200 drop-shadow-lg"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      <div className="text-center">
        <p className="text-[10px] font-mono" style={{ color: "#6b7199" }}>
          #{String(pokemon.id).padStart(3, "0")}
        </p>
        <p className="text-sm font-semibold text-[rgb(225,228,255)] group-hover:text-white transition-colors leading-tight">
          {pokemon.name_fr ?? pokemon.name_en}
        </p>
        {pokemon.name_fr && (
          <p className="text-[10px]" style={{ color: "#6b7199" }}>{pokemon.name_en}</p>
        )}
      </div>

      <div className="flex gap-1.5 flex-wrap justify-center">
        {t1 && <TypeBadge typeName={t1.name_en} label={t1.name_fr ?? t1.name_en} size="sm" />}
        {t2 && <TypeBadge typeName={t2.name_en} label={t2.name_fr ?? t2.name_en} size="sm" />}
      </div>

      <p className="text-[10px] font-mono" style={{ color: "#4a4f75" }}>
        BST {pokemon.bst}
      </p>
    </Link>
  );
}
