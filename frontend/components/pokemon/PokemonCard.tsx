import Link from "next/link";
import Image from "next/image";
import type { PokemonListItem } from "@/types/api";
import { TypeBadge } from "./TypeBadge";
import { basePokemonSprite } from "@/lib/constants";
import { primaryType, secondaryType } from "@/lib/utils";

interface PokemonCardProps {
  pokemon: PokemonListItem;
}

export function PokemonCard({ pokemon }: PokemonCardProps) {
  const spriteUrl = basePokemonSprite(pokemon.national_id ?? pokemon.id);
  const t1 = primaryType(pokemon.types);
  const t2 = secondaryType(pokemon.types);

  return (
    <Link
      href={`/pokedex/${pokemon.id}`}
      className="group flex flex-col items-center gap-2 p-4 rounded-xl bg-[rgb(20,20,28)] border border-[rgb(50,50,70)] hover:border-indigo-500 hover:bg-[rgb(25,25,38)] transition-all duration-200"
    >
      <div className="relative w-20 h-20 flex items-center justify-center">
        <Image
          src={spriteUrl}
          alt={pokemon.name_en}
          width={80}
          height={80}
          unoptimized
          className="object-contain group-hover:scale-110 transition-transform duration-200"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      <div className="text-center">
        <p className="text-xs text-[rgb(120,120,140)]">#{pokemon.id}</p>
        <p className="text-sm font-semibold text-[rgb(220,220,255)] group-hover:text-indigo-300 transition-colors">
          {pokemon.name_fr ?? pokemon.name_en}
        </p>
        <p className="text-xs text-[rgb(100,100,120)]">{pokemon.name_en}</p>
      </div>

      <div className="flex gap-1.5 flex-wrap justify-center">
        {t1 && <TypeBadge typeName={t1.name_en} size="sm" />}
        {t2 && <TypeBadge typeName={t2.name_en} size="sm" />}
      </div>
    </Link>
  );
}
