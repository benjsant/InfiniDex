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
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gradient-to-r from-indigo-700/50 to-purple-700/50 border border-indigo-500/40" style={{ color: "var(--color-if-text-hi)" }}>
        {type.name_fr ?? type.name_en}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide bg-if-input text-if-text-lo">
      {type.name_fr ?? type.name_en}
    </span>
  );
}

function TripleSpriteWithFallback({ id, name, components }: { id: number; name: string; components?: { pokemon_id: number; national_id?: number | null; name_en: string; name_fr?: string | null }[] }) {
  const [failed, setFailed] = useState(false);

  if (!failed) {
    return (
      <img
        src={`/api/triple-fusions/${id}/sprite`}
        alt={name}
        width={112}
        height={112}
        style={{ imageRendering: "pixelated", objectFit: "contain" }}
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <div className="flex flex-col items-center gap-2 px-2">
      <div className="flex gap-1 items-center">
        {components?.map((c, i) => (
          <span key={c.pokemon_id}>
            <img
              src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${c.national_id ?? c.pokemon_id}.png`}
              alt={c.name_fr ?? c.name_en}
              width={32}
              height={32}
              style={{ imageRendering: "pixelated", objectFit: "contain", opacity: 0.5, filter: "grayscale(0.4)" }}
              title={c.name_fr ?? c.name_en}
            />
            {i < (components.length - 1) && (
              <span className="text-[10px]" style={{ color: "var(--color-if-border-hi)" }}>+</span>
            )}
          </span>
        ))}
      </div>
      <p className="text-[10px] text-center leading-tight" style={{ color: "var(--color-if-text-lo)" }}>
        🔒 Découvre ce sprite<br />dans le jeu
      </p>
    </div>
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
    <div className="border border-if-input rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-4 py-3 bg-if-card hover:bg-if-elevated transition-colors text-left"
      >
        <span className="text-xs text-if-muted w-6 shrink-0 font-mono">#{summary.id}</span>
        <span className="font-semibold text-if-text-hi min-w-[130px]">{summary.name_fr ?? summary.name_en}</span>
        <div className="flex flex-wrap gap-1">
          {summary.types.map((t, i) => <TripleTypeBadge key={i} type={t} />)}
        </div>
        <span className="ml-auto text-if-muted shrink-0">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-if-input bg-if-card">
          {isLoading || !detail ? (
            <div className="p-4 animate-pulse space-y-2">
              <div className="h-4 w-48 bg-if-input rounded" />
              <div className="h-4 w-32 bg-if-input rounded" />
            </div>
          ) : (
            <div className="px-4 py-4 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-4">
                {/* Sprite */}
                <div className="flex justify-center sm:justify-start">
                  <div className="w-32 h-32 flex items-center justify-center rounded-xl bg-if-surface border border-if-input">
                    <TripleSpriteWithFallback id={summary.id} name={summary.name_fr ?? summary.name_en} components={detail.components} />
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-2">
                    Composants
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {detail.components.map((c) => (
                      <Link
                        key={c.position}
                        href={`/pokedex/${c.pokemon_id}`}
                        className="px-2 py-1 rounded bg-if-input border border-if-border-mid text-sm hover:border-indigo-500 transition-colors" style={{ color: "var(--color-if-text-dim)" }}
                      >
                        {c.name_fr ?? c.name_en}
                      </Link>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-2">
                    Talents
                  </p>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {detail.abilities.filter((a) => !a.is_hidden).map((a) => (
                      <span key={a.slot} className="px-2 py-1 rounded bg-if-input text-if-text-dim">
                        {a.name_fr ?? a.name_en}
                      </span>
                    ))}
                    {detail.abilities.filter((a) => a.is_hidden).map((a) => (
                      <span key={a.slot} className="px-2 py-1 rounded bg-if-input text-if-text-lo italic">
                        {a.name_fr ?? a.name_en} (caché)
                      </span>
                    ))}
                  </div>
                </div>

                {detail.evolution_level && (
                  <p className="text-xs text-if-text-xs">
                    Evolue au niveau {detail.evolution_level}
                  </p>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-2">
                    Statistiques
                  </p>
                  <div className="space-y-2 max-w-sm">
                    {(["hp","attack","defense","sp_attack","sp_defense","speed"] as const).map((k) => (
                      <StatBar key={k} stat={k} value={detail[k]} />
                    ))}
                    <div className="flex items-center gap-3 pt-1 border-t border-if-input">
                      <span className="w-24 text-right text-xs text-if-text-xs">Total</span>
                      <span className="text-sm font-bold font-mono text-if-text-hi">{baseTotal}</span>
                    </div>
                  </div>
                </div>

                {weaknesses.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-if-muted uppercase tracking-wider mb-2">
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
  const { data: list = [], isLoading, error } = useQuery({
    queryKey: ["triple-fusions"],
    queryFn: getTripleFusions,
    staleTime: 5 * 60 * 1000,
  });

  const [spoilerRevealed, setSpoilerRevealed] = useState(false);
  const byId = new Map(list.map((tf) => [tf.id, tf]));

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2 text-if-text-hi">Triple Fusions</h1>
      <p className="text-sm text-if-text-xs mb-6">
        Pokémon exclusifs à Pokémon Infinite Fusion obtenus en fusionnant trois Pokémon simultanément.
      </p>

      {!spoilerRevealed ? (
        <div className="rounded-xl border-2 p-8 text-center space-y-4" style={{ borderColor: "rgba(232,184,75,0.5)", background: "var(--color-if-elevated)" }}>
          <p className="font-bold text-lg" style={{ color: "var(--color-if-text-hi)" }}>⚠ Attention — Spoilers</p>
          <p className="text-sm max-w-lg mx-auto leading-relaxed" style={{ color: "var(--color-if-text-dim)" }}>
            Cette page révèle l&apos;existence et les détails de Pokémon secrets qui se débloquent
            en progressant dans le jeu. Si tu veux les découvrir par toi-même, reviens plus tard.
          </p>
          <button
            onClick={() => setSpoilerRevealed(true)}
            className="mt-2 px-6 py-2 rounded-lg font-semibold transition-colors text-sm"
            style={{ background: "var(--color-if-accent)", border: "1px solid rgba(232,184,75,0.6)", color: "#0d0f28" }}
          >
            J&apos;accepte les spoilers — afficher le contenu
          </button>
        </div>
      ) : (
        <>
          <div className="rounded-lg bg-if-card border border-if-border-mid p-4 mb-6 text-sm space-y-2" style={{ color: "var(--color-if-text-dim)" }}>
            <p>
              Les <span className="font-semibold" style={{ color: "var(--color-if-text-hi)" }}>Triple Fusions</span> résultent de la fusion
              simultanée de trois Pokémon (un trio légendaire ou les trois starters d&apos;une génération).
            </p>
            <p>
              Elles possèdent des{" "}
              <span className="inline-flex items-center mx-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-gradient-to-r from-indigo-700/50 to-purple-700/50 border border-indigo-500/40" style={{ color: "var(--color-if-text-hi)" }}>
                types propres à IF
              </span>{" "}
              qui n&apos;existent pas dans les jeux officiels, avec des efficacités personnalisées.
              Cliquer sur une entrée pour voir les détails.
            </p>
          </div>

          {error && (
            <p className="text-red-400 text-sm py-4 text-center">
              Erreur de chargement : {(error as Error).message}
            </p>
          )}
          {isLoading ? (
            <div className="space-y-2 animate-pulse">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-12 rounded-lg bg-if-elevated" />
              ))}
            </div>
          ) : (
            <div className="space-y-8">
              {GROUPS.map((group) => {
                const entries = group.ids.map((id) => byId.get(id)).filter(Boolean) as TripleFusionListItem[];
                if (entries.length === 0) return null;
                return (
                  <div key={group.label}>
                    <h2 className="text-xs font-semibold text-if-muted uppercase tracking-widest mb-3 border-b border-if-input pb-1">
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
