"use client";

import { useState, use } from "react";
import Image from "next/image";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
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
import { basePokemonSprite, typeColor } from "@/lib/constants";
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

  const primaryColor = t1 ? (typeColor(t1.name_en)) : "#6366f1";

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div
        className="rounded-2xl p-4 sm:p-6 mb-6 overflow-hidden relative"
        style={{
          background: `linear-gradient(135deg, #111428 50%, ${primaryColor}18)`,
          border: "1px solid #1e2240",
          boxShadow: `0 4px 24px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)`,
        }}
      >
        {/* Top accent line */}
        <div
          className="absolute top-0 left-0 right-0 h-0.5 rounded-t-2xl"
          style={{ background: `linear-gradient(90deg, transparent, ${primaryColor}, transparent)` }}
        />

        <div className="flex flex-col sm:flex-row gap-5">
          {/* Sprites */}
          <div className="flex gap-3 shrink-0 justify-center sm:justify-start">
            {[
              { label: "Base", node: <Image src={spriteUrl} alt={pokemon.name_en} width={96} height={96} unoptimized className="object-contain" /> },
              { label: "Auto-fusion", node: <FusionSprite headId={pokemonId} bodyId={pokemonId} size={96} /> },
            ].map(({ label, node }) => (
              <div key={label} className="flex flex-col items-center gap-1">
                <div
                  className="flex items-center justify-center w-28 h-28 rounded-xl"
                  style={{ background: "#0f1225", border: "1px solid #1e2240" }}
                >
                  {node}
                </div>
                <span className="text-[10px]" style={{ color: "#6b7199" }}>{label}</span>
              </div>
            ))}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div>
                <p className="text-xs font-mono" style={{ color: "#6b7199" }}>
                  IF #{String(pokemon.id).padStart(3, "0")}
                  {pokemon.national_id && ` · #${String(pokemon.national_id).padStart(3, "0")} National`}
                </p>
                <h1 className="text-2xl sm:text-3xl font-bold" style={{ color: "#e1e4ff" }}>
                  {pokemon.name_fr ?? pokemon.name_en}
                </h1>
                {pokemon.name_fr && (
                  <p className="text-base" style={{ color: "#6b7199" }}>{pokemon.name_en}</p>
                )}
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

            <div className="flex gap-2 mt-3 flex-wrap">
              {t1 && <TypeBadge typeName={t1.name_en} label={t1.name_fr ?? t1.name_en} />}
              {t2 && <TypeBadge typeName={t2.name_en} label={t2.name_fr ?? t2.name_en} />}
            </div>

            {pokemon.abilities.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3 text-sm">
                {normalAbilities.map((a) => (
                  <span
                    key={a.slot}
                    className="px-2 py-1 rounded-lg text-sm"
                    style={{ background: "#1e2240", color: "#e1e4ff", border: "1px solid #2d3260" }}
                  >
                    {a.name_fr ?? a.name_en}
                  </span>
                ))}
                {hiddenAbility && (
                  <span
                    className="px-2 py-1 rounded-lg text-sm italic"
                    style={{ background: "#1e2240", color: "#6b7199", border: "1px solid #2d3260" }}
                  >
                    {hiddenAbility.name_fr ?? hiddenAbility.name_en} (caché)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0.5 mb-6 overflow-x-auto" style={{ borderBottom: "1px solid #1e2240" }}>
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className="px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-all -mb-px"
            style={{
              borderBottomColor: activeTab === key ? "#e8b84b" : "transparent",
              color: activeTab === key ? "#e8b84b" : "#6b7199",
            }}
          >
            {label}
            {key === "moves" && moves.length > 0 && (
              <span className="ml-1 text-xs" style={{ color: "#6b7199" }}>({moves.length})</span>
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
          <p className="text-sm" style={{ color: "#6b7199" }}>
            Sélectionne un partenaire pour voir la fusion.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href={`/fusion?head=${pokemonId}`}
              className="flex-1 px-4 py-3 rounded-xl text-center transition-all if-panel if-glow-hover"
            >
              <p className="text-xs mb-1" style={{ color: "#6b7199" }}>{pokemon.name_fr ?? pokemon.name_en} en tant que…</p>
              <p className="font-semibold" style={{ color: "#e8b84b" }}>Tête (Head)</p>
            </Link>
            <Link
              href={`/fusion?body=${pokemonId}`}
              className="flex-1 px-4 py-3 rounded-xl text-center transition-all if-panel if-glow-hover"
            >
              <p className="text-xs mb-1" style={{ color: "#6b7199" }}>{pokemon.name_fr ?? pokemon.name_en} en tant que…</p>
              <p className="font-semibold" style={{ color: "#e8b84b" }}>Corps (Body)</p>
            </Link>
          </div>
          <Link href="/fusion" className="text-sm transition-colors" style={{ color: "#e8b84b" }}>
            Ouvrir le calculateur de fusion complet <ChevronRight size={14} className="inline" />
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
      <p style={{ color: "#6b7199" }}>Pokémon #{id} introuvable.</p>
      <Link href="/pokedex" className="mt-4 block transition-colors" style={{ color: "#e8b84b" }}>
        <ChevronLeft size={14} className="inline" /> Retour au Pokédex
      </Link>
    </div>
  );
}
