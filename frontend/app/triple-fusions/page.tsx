"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getTripleFusions, getTripleFusion, getTripleFusionWeaknesses } from "@/lib/api";
import { StatBar } from "@/components/pokemon/StatBar";
import { WeaknessGrid } from "@/components/pokemon/WeaknessGrid";
import type { TripleFusionListItem, TripleFusionDetail, TripleFusionTypeOut, WeaknessOut } from "@/types/api";

const GROUPS: { label: string; ids: number[] }[] = [
  { label: "Trios légendaires", ids: [1, 2, 3, 4, 5, 6, 7, 8] },
  { label: "Starters Gén. 1",   ids: [9, 10, 11] },
  { label: "Starters Gén. 2",   ids: [12, 13, 14] },
  { label: "Starters Gén. 3",   ids: [15, 16, 17] },
  { label: "Starters Gén. 4",   ids: [18, 19, 20] },
  { label: "Starters Gén. 6",   ids: [21, 22, 23] },
];

function TripleTypeBadge({ type }: { type: TripleFusionTypeOut }) {
  if (type.is_triple_fusion_type) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gradient-to-r from-indigo-700/50 to-purple-700/50 border border-indigo-500/40 text-indigo-200">
        {type.name_fr ?? type.name_en}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide bg-[rgb(40,40,55)] text-[rgb(180,180,210)]">
      {type.name_fr ?? type.name_en}
    </span>
  );
}

function FusionRow({ summary }: { summary: TripleFusionListItem }) {
  const [expanded, setExpanded] = useState(false);

  const { data: detail, isLoading } = useQuery<TripleFusionDetail>({
    queryKey: ["triple-fusion", summary.id],
    queryFn: () => getTripleFusion(summary.id),
    enabled: expanded,
    staleTime: Infinity,
  });

  const { data: weaknesses = [] } = useQuery<WeaknessOut[]>({
    queryKey: ["triple-fusion-weaknesses", summary.id],
    queryFn: () => getTripleFusionWeaknesses(summary.id),
    enabled: expanded,
    staleTime: Infinity,
  });

  const baseTotal = detail
    ? detail.hp + detail.attack + detail.defense + detail.sp_attack + detail.sp_defense + detail.speed
    : null;

  return (
    <div className="border border-[rgb(40,40,55)] rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-4 py-3 bg-[rgb(20,20,28)] hover:bg-[rgb(25,25,38)] transition-colors text-left"
      >
        <span className="text-xs text-[rgb(80,80,100)] w-6 shrink-0 font-mono">#{summary.id}</span>
        <span className="font-semibold text-[rgb(220,220,255)] min-w-[130px]">{summary.name_en}</span>
        <div className="flex flex-wrap gap-1">
          {summary.types.map((t, i) => <TripleTypeBadge key={i} type={t} />)}
        </div>
        <span className="ml-auto text-[rgb(100,100,130)] shrink-0">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-[rgb(35,35,50)] bg-[rgb(18,18,26)]">
          {isLoading || !detail ? (
            <div className="p-4 animate-pulse space-y-2">
              <div className="h-4 w-48 bg-[rgb(30,30,42)] rounded" />
              <div className="h-4 w-32 bg-[rgb(30,30,42)] rounded" />
            </div>
          ) : (
            <div className="px-4 py-4 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-4">
                {/* Sprite */}
                <div className="flex justify-center sm:justify-start">
                  <div className="w-32 h-32 flex items-center justify-center rounded-xl bg-[rgb(15,15,22)] border border-[rgb(40,40,55)]">
                    <img
                      src={`/api/triple-fusions/${summary.id}/sprite`}
                      alt={summary.name_en}
                      width={112}
                      height={112}
                      style={{ imageRendering: "pixelated", objectFit: "contain" }}
                    />
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-[rgb(100,100,130)] uppercase tracking-wider mb-2">
                    Composants
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {detail.components.map((c) => (
                      <Link
                        key={c.position}
                        href={`/pokedex/${c.pokemon_id}`}
                        className="px-2 py-1 rounded bg-[rgb(30,30,45)] border border-[rgb(50,50,70)] text-sm text-indigo-300 hover:border-indigo-500 transition-colors"
                      >
                        {c.name_fr ?? c.name_en}
                      </Link>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-[rgb(100,100,130)] uppercase tracking-wider mb-2">
                    Talents
                  </p>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {detail.abilities.filter((a) => !a.is_hidden).map((a) => (
                      <span key={a.slot} className="px-2 py-1 rounded bg-[rgb(30,30,42)] text-[rgb(200,200,220)]">
                        {a.name_fr ?? a.name_en}
                      </span>
                    ))}
                    {detail.abilities.filter((a) => a.is_hidden).map((a) => (
                      <span key={a.slot} className="px-2 py-1 rounded bg-[rgb(30,30,42)] text-[rgb(160,160,180)] italic">
                        {a.name_fr ?? a.name_en} (caché)
                      </span>
                    ))}
                  </div>
                </div>

                {detail.evolution_level && (
                  <p className="text-xs text-[rgb(120,120,140)]">
                    Evolue au niveau {detail.evolution_level}
                  </p>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-[rgb(100,100,130)] uppercase tracking-wider mb-2">
                    Statistiques
                  </p>
                  <div className="space-y-2 max-w-sm">
                    {(["hp","attack","defense","sp_attack","sp_defense","speed"] as const).map((k) => (
                      <StatBar key={k} stat={k} value={detail[k]} />
                    ))}
                    <div className="flex items-center gap-3 pt-1 border-t border-[rgb(40,40,55)]">
                      <span className="w-24 text-right text-xs text-[rgb(120,120,140)]">Total</span>
                      <span className="text-sm font-bold font-mono text-[rgb(220,220,255)]">{baseTotal}</span>
                    </div>
                  </div>
                </div>

                {weaknesses.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-[rgb(100,100,130)] uppercase tracking-wider mb-2">
                      Faiblesses & Résistances
                    </p>
                    <WeaknessGrid weaknesses={weaknesses} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TripleFusionsPage() {
  const { data: list = [], isLoading } = useQuery({
    queryKey: ["triple-fusions"],
    queryFn: getTripleFusions,
    staleTime: Infinity,
  });

  const [spoilerRevealed, setSpoilerRevealed] = useState(false);
  const byId = new Map(list.map((tf) => [tf.id, tf]));

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2 text-[rgb(220,220,255)]">Triple Fusions</h1>
      <p className="text-sm text-[rgb(120,120,140)] mb-6">
        Pokémon exclusifs à Pokémon Infinite Fusion obtenus en fusionnant trois Pokémon simultanément.
      </p>

      {!spoilerRevealed ? (
        <div className="rounded-xl border-2 border-amber-700/50 bg-amber-950/25 p-8 text-center space-y-4">
          <p className="text-amber-400 font-bold text-lg">Attention — Spoilers</p>
          <p className="text-sm text-[rgb(200,185,150)] max-w-lg mx-auto leading-relaxed">
            Cette page révèle l&apos;existence et les détails de Pokémon secrets qui se débloquent
            en progressant dans le jeu. Si tu veux les découvrir par toi-même, reviens plus tard.
          </p>
          <button
            onClick={() => setSpoilerRevealed(true)}
            className="mt-2 px-6 py-2 rounded-lg bg-amber-800/50 hover:bg-amber-700/50 border border-amber-700/40 text-amber-200 font-semibold transition-colors text-sm"
          >
            J&apos;accepte les spoilers — afficher le contenu
          </button>
        </div>
      ) : (
        <>
          <div className="rounded-lg bg-[rgb(20,20,30)] border border-[rgb(50,50,70)] p-4 mb-6 text-sm text-[rgb(160,160,180)] space-y-2">
            <p>
              Les <span className="text-indigo-300 font-semibold">Triple Fusions</span> résultent de la fusion
              simultanée de trois Pokémon (un trio légendaire ou les trois starters d&apos;une génération).
            </p>
            <p>
              Elles possèdent des{" "}
              <span className="inline-flex items-center mx-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-gradient-to-r from-indigo-700/50 to-purple-700/50 border border-indigo-500/40 text-indigo-200">
                types propres à IF
              </span>{" "}
              qui n&apos;existent pas dans les jeux officiels, avec des efficacités personnalisées.
              Cliquer sur une entrée pour voir les détails.
            </p>
          </div>

          {isLoading ? (
            <div className="space-y-2 animate-pulse">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-12 rounded-lg bg-[rgb(25,25,35)]" />
              ))}
            </div>
          ) : (
            <div className="space-y-8">
              {GROUPS.map((group) => {
                const entries = group.ids.map((id) => byId.get(id)).filter(Boolean) as TripleFusionListItem[];
                if (entries.length === 0) return null;
                return (
                  <div key={group.label}>
                    <h2 className="text-xs font-semibold text-[rgb(100,100,140)] uppercase tracking-widest mb-3 border-b border-[rgb(35,35,50)] pb-1">
                      {group.label}
                    </h2>
                    <div className="space-y-2">
                      {entries.map((tf) => (
                        <FusionRow key={tf.id} summary={tf} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
