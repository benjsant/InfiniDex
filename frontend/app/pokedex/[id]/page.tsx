"use client";

import { useState, use } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  usePokemon,
  usePokemonMoves,
  usePokemonEvolutions,
  usePokemonWeaknesses,
} from "@/hooks/usePokemon";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { StatBar } from "@/components/pokemon/StatBar";
import { MovesetTable } from "@/components/pokemon/MovesetTable";
import { EvolutionChain } from "@/components/pokemon/EvolutionChain";
import { WeaknessGrid } from "@/components/pokemon/WeaknessGrid";
import { AiSuggestButton } from "@/components/ai/AiSuggestButton";
import { basePokemonSprite } from "@/lib/constants";
import { primaryType, secondaryType, cn } from "@/lib/utils";
import { FusionSprite } from "@/components/fusion/FusionSprite";

type Tab = "stats" | "moves" | "evolutions" | "weaknesses" | "fusion";

const TABS: { key: Tab; label: string }[] = [
  { key: "stats",      label: "Stats" },
  { key: "moves",      label: "Capacités" },
  { key: "evolutions", label: "Évolutions" },
  { key: "weaknesses", label: "Faiblesses" },
  { key: "fusion",     label: "Fusion" },
];

export default function PokemonDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const pokemonId = parseInt(id, 10);
  const [activeTab, setActiveTab] = useState<Tab>("stats");

  const { data: pokemon, isLoading } = usePokemon(pokemonId);
  const { data: moves = [] }        = usePokemonMoves(pokemonId,    { enabled: activeTab === "moves" });
  const { data: evolutions = [] }   = usePokemonEvolutions(pokemonId, { enabled: activeTab === "evolutions" });
  const { data: weaknesses = [] }   = usePokemonWeaknesses(pokemonId, { enabled: activeTab === "weaknesses" });

  if (isLoading) return <PageSkeleton />;
  if (!pokemon)  return <NotFound id={pokemonId} />;

  const spriteUrl = basePokemonSprite(pokemon.national_id ?? pokemonId);

  const t1 = primaryType(pokemon.types);
  const t2 = secondaryType(pokemon.types);

  const normalAbilities = pokemon.abilities.filter((a) => !a.is_hidden);
  const hiddenAbility   = pokemon.abilities.find((a) => a.is_hidden);

  const stats = [
    { key: "hp",         value: pokemon.hp },
    { key: "attack",     value: pokemon.attack },
    { key: "defense",    value: pokemon.defense },
    { key: "sp_attack",  value: pokemon.sp_attack },
    { key: "sp_defense", value: pokemon.sp_defense },
    { key: "speed",      value: pokemon.speed },
  ];

  const baseTotal = stats.reduce((s, st) => s + st.value, 0);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-6 mb-6">
        {/* Sprites : base + self-fusion */}
        <div className="flex gap-3 shrink-0 mx-auto sm:mx-0">
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center justify-center w-32 h-32 rounded-xl bg-[rgb(20,20,28)] border border-[rgb(50,50,70)]">
              <Image
                src={spriteUrl}
                alt={pokemon.name_en}
                width={104}
                height={104}
                unoptimized
                className="object-contain"
              />
            </div>
            <span className="text-[10px] text-[rgb(100,100,120)]">Base</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center justify-center w-32 h-32 rounded-xl bg-[rgb(20,20,28)] border border-[rgb(50,50,70)]">
              <FusionSprite headId={pokemonId} bodyId={pokemonId} size={104} />
            </div>
            <span className="text-[10px] text-[rgb(100,100,120)]">Auto-fusion</span>
          </div>
        </div>

        <div className="flex-1">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              <p className="text-sm text-[rgb(120,120,140)]">
                IF #{pokemon.id}
                {pokemon.national_id && ` · National #${pokemon.national_id}`}
              </p>
              <h1 className="text-3xl font-bold text-[rgb(220,220,255)]">
                {pokemon.name_fr ?? pokemon.name_en}
              </h1>
              <p className="text-lg text-[rgb(160,160,180)]">{pokemon.name_en}</p>
            </div>
            <AiSuggestButton
              pokemonName={pokemon.name_en}
              pokemonId={pokemonId}
              context={[
                `Pokémon consulté : ${pokemon.name_en}${pokemon.name_fr ? ` / ${pokemon.name_fr}` : ""} (IF #${pokemon.id}${pokemon.national_id ? `, National #${pokemon.national_id}` : ""})`,
                `Types : ${[t1, t2].filter(Boolean).map(t => t!.name_en).join(" / ")}`,
                `Stats : HP ${pokemon.hp} / Atk ${pokemon.attack} / Def ${pokemon.defense} / SpA ${pokemon.sp_attack} / SpD ${pokemon.sp_defense} / Spe ${pokemon.speed}`,
              ].join(" · ")}
            />
          </div>

          <div className="flex gap-2 mt-3">
            {t1 && <TypeBadge typeName={t1.name_en} />}
            {t2 && <TypeBadge typeName={t2.name_en} />}
          </div>

          {pokemon.abilities.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 text-sm">
              {normalAbilities.map((a) => (
                <span key={a.slot} className="px-2 py-1 rounded bg-[rgb(30,30,42)] text-[rgb(200,200,220)]">
                  {a.name_fr ?? a.name_en}
                </span>
              ))}
              {hiddenAbility && (
                <span className="px-2 py-1 rounded bg-[rgb(30,30,42)] text-[rgb(160,160,180)] italic">
                  {hiddenAbility.name_fr ?? hiddenAbility.name_en} (caché)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[rgb(40,40,55)] mb-6 overflow-x-auto">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              "px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-all -mb-px",
              activeTab === key
                ? "border-indigo-500 text-indigo-300"
                : "border-transparent text-[rgb(120,120,140)] hover:text-[rgb(200,200,220)]",
            )}
          >
            {label}
            {key === "moves" && moves.length > 0 && (
              <span className="ml-1 text-xs text-[rgb(100,100,120)]">({moves.length})</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "stats" && (
        <div className="space-y-3 max-w-lg">
          {stats.map(({ key, value }) => (
            <StatBar key={key} stat={key} value={value} />
          ))}
          <div className="flex items-center gap-3 pt-2 border-t border-[rgb(40,40,55)]">
            <span className="w-24 text-right text-xs text-[rgb(120,120,140)]">Total</span>
            <span className="w-8 text-right text-sm font-bold font-mono text-[rgb(220,220,255)]">
              {baseTotal}
            </span>
          </div>
        </div>
      )}

      {activeTab === "moves" && (
        moves.length > 0
          ? <MovesetTable moves={moves} />
          : <p className="text-[rgb(120,120,140)] text-sm">Aucune capacité chargée.</p>
      )}

      {activeTab === "evolutions" && (
        <EvolutionChain pokemonId={pokemonId} evolutions={evolutions} />
      )}

      {activeTab === "weaknesses" && (
        <WeaknessGrid weaknesses={weaknesses} />
      )}

      {activeTab === "fusion" && (
        <div className="space-y-4">
          <p className="text-sm text-[rgb(160,160,180)]">
            Sélectionne un partenaire pour voir la fusion.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href={`/fusion?head=${pokemonId}`}
              className="flex-1 px-4 py-3 rounded-lg bg-[rgb(25,25,35)] border border-[rgb(40,40,55)] hover:border-indigo-500 transition-all text-center"
            >
              <p className="text-xs text-[rgb(120,120,140)] mb-1">{pokemon.name_fr ?? pokemon.name_en} en tant que…</p>
              <p className="font-semibold text-indigo-400">Tête (Head)</p>
            </Link>
            <Link
              href={`/fusion?body=${pokemonId}`}
              className="flex-1 px-4 py-3 rounded-lg bg-[rgb(25,25,35)] border border-[rgb(40,40,55)] hover:border-indigo-500 transition-all text-center"
            >
              <p className="text-xs text-[rgb(120,120,140)] mb-1">{pokemon.name_fr ?? pokemon.name_en} en tant que…</p>
              <p className="font-semibold text-purple-400">Corps (Body)</p>
            </Link>
          </div>
          <Link href="/fusion" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
            → Ouvrir le calculateur de fusion complet
          </Link>
        </div>
      )}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 animate-pulse">
      <div className="flex gap-6 mb-6">
        <div className="w-36 h-36 rounded-xl bg-[rgb(25,25,35)]" />
        <div className="flex-1 space-y-3">
          <div className="h-4 w-20 bg-[rgb(35,35,50)] rounded" />
          <div className="h-8 w-48 bg-[rgb(35,35,50)] rounded" />
        </div>
      </div>
    </div>
  );
}

function NotFound({ id }: { id: number }) {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 text-center">
      <p className="text-[rgb(120,120,140)]">Pokémon #{id} introuvable.</p>
      <Link href="/pokedex" className="mt-4 text-indigo-400 hover:text-indigo-300 transition-colors block">
        ← Retour au Pokédex
      </Link>
    </div>
  );
}
