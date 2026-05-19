"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ArrowLeftRight, Star, Link2, Check, Shuffle } from "lucide-react";
import { useFusionFull, useFusionAbilities, useSprites } from "@/hooks/useFusion";
import { useToast } from "@/components/layout/Toast";
import { useHistory } from "@/hooks/useHistory";
import { useFavorites } from "@/hooks/useFavorites";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { StatBar } from "@/components/pokemon/StatBar";
import { effectiveness, ALL_TYPES, TYPE_FR } from "@/lib/typeChart";
import { SectionErrorBoundary } from "@/components/layout/ErrorBoundary";
import { AiSuggestButton } from "@/components/ai/AiSuggestButton";
import { FusionMovesetTable } from "@/components/fusion/FusionMovesetTable";
import { SpriteCarousel } from "@/components/fusion/SpriteCarousel";

export default function FusionResultPage({
  params,
}: {
  params: Promise<{ headId: string; bodyId: string }>;
}) {
  const { headId, bodyId } = use(params);
  const hId = parseInt(headId, 10);
  const bId = parseInt(bodyId, 10);

  const { data: full, isLoading, error }                     = useFusionFull(hId, bId);
  const fusion                                               = full?.fusion;
  const moves                                                = full?.moves ?? [];
  const expertMoves                                          = full?.expert_moves ?? [];
  const { data: abilities = [] }                             = useFusionAbilities(hId, bId);
  const { data: sprites = [], isLoading: spritesLoading }    = useSprites(hId, bId);
  const { data: spritesReversed = [], isLoading: spritesRevLoading } = useSprites(bId, hId);
  const { addEntry }                                         = useHistory();
  const { isFavorite, toggleFavorite }                       = useFavorites();
  const { toast }                                            = useToast();
  const router                                               = useRouter();

  const [copied, setCopied]       = useState(false);
  const [shuffling, setShuffling] = useState(false);

  const handleShuffle = useCallback(async () => {
    setShuffling(true);
    try {
      const r = await fetch("/api/fusion/random");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      if (data?.head_id && data?.body_id) {
        router.push(`/fusion/${data.head_id}/${data.body_id}`);
      } else {
        toast("Impossible d'obtenir une fusion aléatoire", "error");
      }
    } catch {
      toast("Erreur réseau, réessaie.", "error");
    } finally {
      setShuffling(false);
    }
  }, [router, toast]);

  // Defensive coverage — computed from fusion's type combination
  const defensiveCoverage = useMemo(() => {
    const t1 = fusion?.type1?.name_en;
    const t2 = fusion?.type2?.name_en ?? null;
    if (!t1) return null;

    const mult = (atk: string) =>
      effectiveness(atk, t1) * (t2 ? effectiveness(atk, t2) : 1);

    return {
      quad:    ALL_TYPES.filter((t) => mult(t) >= 4),
      double:  ALL_TYPES.filter((t) => mult(t) === 2),
      half:    ALL_TYPES.filter((t) => mult(t) === 0.5),
      quarter: ALL_TYPES.filter((t) => mult(t) === 0.25),
      immune:  ALL_TYPES.filter((t) => mult(t) === 0),
    };
  }, [fusion]);

  // Rich AI context — built once all async data is loaded
  const aiContext = useMemo(() => {
    if (!fusion) return undefined;
    const types = [fusion.type1?.name_en, fusion.type2?.name_en].filter(Boolean).join("/");
    const bst   = fusion.hp + fusion.attack + fusion.defense + fusion.sp_attack + fusion.sp_defense + fusion.speed;

    const parts: string[] = [
      `Fusion: ${fusion.head_name_fr ?? fusion.head_name_en} (tête #${fusion.head_id}) / ${fusion.body_name_fr ?? fusion.body_name_en} (corps #${fusion.body_id})`,
      `Types: ${types || "?"}`,
      `Stats: HP ${fusion.hp} Atk ${fusion.attack} Déf ${fusion.defense} AtkSpé ${fusion.sp_attack} DéfSpé ${fusion.sp_defense} Vit ${fusion.speed} (BST ${bst})`,
    ];

    if (abilities.length > 0) {
      const abilityStr = abilities
        .map((a) => `${a.name_fr ?? a.name_en}${a.is_hidden ? " [caché]" : ""} (${a.origin === "head" ? "tête" : "corps"})`)
        .join(", ");
      parts.push(`Talents: ${abilityStr}`);
    }

    const topMoves = [...moves]
      .filter((m) => m.category !== "status" && (m.power ?? 0) > 0)
      .sort((a, b) => (b.power ?? 0) - (a.power ?? 0))
      .slice(0, 6);
    if (topMoves.length > 0) {
      const moveStr = topMoves.map((m) => `${m.name_fr ?? m.name_en} (${m.type.name_en}, ${m.power})`).join(", ");
      parts.push(`Top capacités offensives: ${moveStr}`);
    }

    return parts.join(". ") + ".";
  }, [fusion, abilities, moves]);


  useEffect(() => {
    if (fusion) {
      addEntry({
        headId: hId,
        bodyId: bId,
        headName: fusion.head_name_fr ?? fusion.head_name_en,
        bodyName: fusion.body_name_fr ?? fusion.body_name_en,
      });
    }
  // addEntry is stable (useCallback), fusion identity changes only when data arrives
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fusion]);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 animate-pulse space-y-4">
        <div className="h-8 w-64 bg-if-input rounded" />
        <div className="h-48 w-48 bg-if-input rounded-xl mx-auto" />
      </div>
    );
  }

  if (error || !fusion) {
    const status = error ? (error as Error & { status?: number }).status : undefined;
    const msg =
      status === 429 ? "Trop de requêtes — réessayez dans quelques secondes."
      : status !== undefined && status >= 500 ? "Erreur serveur — réessayez plus tard."
      : "Fusion introuvable.";
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <p className="text-if-text-xs">{msg}</p>
        <Link href="/fusion" className="mt-4 block transition-colors" style={{ color: "#e8b84b" }}>
          <ChevronLeft size={14} className="inline" /> Retour au calculateur
        </Link>
      </div>
    );
  }

  const fusionName = `${fusion.head_name_fr ?? fusion.head_name_en}/${fusion.body_name_fr ?? fusion.body_name_en}`;
  const reversedName = `${fusion.body_name_fr ?? fusion.body_name_en}/${fusion.head_name_fr ?? fusion.head_name_en}`;

  const stats = [
    { key: "hp",         value: fusion.hp },
    { key: "attack",     value: fusion.attack },
    { key: "defense",    value: fusion.defense },
    { key: "sp_attack",  value: fusion.sp_attack },
    { key: "sp_defense", value: fusion.sp_defense },
    { key: "speed",      value: fusion.speed },
  ];

  const baseTotal = stats.reduce((s, st) => s + st.value, 0);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      toast("Lien copié !");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const favorited   = isFavorite(hId, bId);

  const handleToggleFavorite = () => {
    const wasFav = favorited;
    toggleFavorite({ headId: hId, bodyId: bId, headName: fusion.head_name_fr ?? fusion.head_name_en, bodyName: fusion.body_name_fr ?? fusion.body_name_en });
    toast(wasFav ? "Retiré des favoris" : "Ajouté aux favoris", wasFav ? "info" : "success");
  };


  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 text-sm text-if-text-xs">
          <Link href="/fusion" className="transition-colors hover:text-[#e8b84b]">Fusion</Link>
          <span>/</span>
          <span className="text-if-text-dim">{fusionName}</span>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleShuffle}
            disabled={shuffling}
            aria-label="Fusion aléatoire"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: "var(--color-if-card)",
              border: "1px solid var(--color-if-border)",
              color: "var(--color-if-muted)",
              opacity: shuffling ? 0.5 : 1,
            }}
          >
            <Shuffle size={13} className={shuffling ? "animate-spin" : ""} />
            Aléatoire
          </button>
          <button
            onClick={handleCopyLink}
            aria-label="Copier le lien"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: copied ? "rgba(74,222,128,0.12)" : "var(--color-if-card)",
              border: `1px solid ${copied ? "#4ade8066" : "var(--color-if-border)"}`,
              color: copied ? "#4ade80" : "var(--color-if-muted)",
            }}
          >
            {copied ? <Check size={13} /> : <Link2 size={13} />}
            {copied ? "Copié !" : "Lien"}
          </button>
          <button
            onClick={handleToggleFavorite}
            aria-label={favorited ? "Retirer des favoris" : "Ajouter aux favoris"}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: favorited ? "rgba(232,184,75,0.15)" : "var(--color-if-card)",
              border: `1px solid ${favorited ? "#e8b84b66" : "var(--color-if-border)"}`,
              color: favorited ? "#e8b84b" : "var(--color-if-muted)",
            }}
          >
            <Star size={13} fill={favorited ? "currentColor" : "none"} />
            {favorited ? "Favori" : "Favori"}
          </button>

        </div>
      </div>

      {/* Main card */}
      <div className="rounded-xl p-4 sm:p-6 mb-6" style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}>
        {/* Sprites row */}
        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start mb-6">
          {/* Normal sprite — carrousel si plusieurs variants */}
          <div className="flex flex-col items-center gap-1">
            <SpriteCarousel headId={hId} bodyId={bId} sprites={sprites} size={128} loading={spritesLoading} />
            <p className="text-xs font-medium" style={{ color: "var(--color-if-text-xs)" }}>{fusionName}</p>
          </div>

          <div className="hidden sm:flex items-center self-center text-if-elevated"><ArrowLeftRight size={20} /></div>

          {/* Reversed sprite */}
          <Link href={`/fusion/${bId}/${hId}`} className="group opacity-70 hover:opacity-100 transition-opacity">
            <div className="flex flex-col items-center gap-1">
              <SpriteCarousel headId={bId} bodyId={hId} sprites={spritesReversed} size={128} loading={spritesRevLoading} />
              <p className="text-xs font-medium" style={{ color: "var(--color-if-text-xs)" }}>{reversedName}</p>
            </div>
          </Link>
        </div>

        {/* Name + types */}
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-if-text-hi mb-1">{fusionName}</h1>
          <div className="flex gap-2 justify-center sm:justify-start mb-1 text-xs text-if-text-xs">
            <span>
              Tête :{" "}
              <Link href={`/pokedex/${hId}`} className="transition-colors" style={{ color: "#e8b84b" }}>
                {fusion.head_name_fr ?? fusion.head_name_en} #{hId}
              </Link>
            </span>
            <span style={{ color: "var(--color-if-border-hi)" }}>·</span>
            <span>
              Corps :{" "}
              <Link href={`/pokedex/${bId}`} className="transition-colors" style={{ color: "#e8b84b" }}>
                {fusion.body_name_fr ?? fusion.body_name_en} #{bId}
              </Link>
            </span>
          </div>
          <div className="flex gap-2 justify-center sm:justify-start">
            {fusion.type1 && <TypeBadge typeName={fusion.type1.name_en} label={fusion.type1.name_fr ?? fusion.type1.name_en} />}
            {fusion.type2 && <TypeBadge typeName={fusion.type2.name_en} label={fusion.type2.name_fr ?? fusion.type2.name_en} />}
          </div>

          {abilities.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 justify-center sm:justify-start">
              {abilities.map((a) => (
                <span
                  key={a.ability_id}
                  className="px-2 py-0.5 rounded-lg text-xs"
                  style={{
                    background: a.is_hidden ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.05)",
                    border: `1px solid ${a.is_hidden ? "#6366f144" : "var(--color-if-border)"}`,
                    color: a.is_hidden ? "#818cf8" : "#9499c0",
                  }}
                  title={`Depuis ${a.origin === "head" ? "la tête" : "le corps"}`}
                >
                  {a.name_fr ?? a.name_en}
                  {a.is_hidden && <span className="ml-1 opacity-60">(caché)</span>}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <SectionErrorBoundary label="Stats">
      <div className="rounded-xl bg-if-card border border-if-border-mid p-5 mb-4">
        <h2 className="text-sm font-semibold text-if-text-xs uppercase tracking-wider mb-4">
          Statistiques fusionnées
        </h2>
        <div className="space-y-3 max-w-md">
          {stats.map(({ key, value }) => (
            <StatBar key={key} stat={key} value={value} />
          ))}
          <div className="flex items-center gap-3 pt-2 border-t border-if-input">
            <span className="w-24 text-right text-xs text-if-text-xs">Total</span>
            <span className="text-sm font-bold font-mono text-if-text-hi">{baseTotal}</span>
          </div>
        </div>
        <p className="text-xs text-if-muted mt-4">
          Physique (HP/Atk/Déf/Vit) = ⌊Body×⅔ + Head×⅓⌋ · Spécial (AtkSpé/DéfSpé) = ⌊Head×⅔ + Body×⅓⌋
        </p>
      </div>
      </SectionErrorBoundary>

      {/* Defensive coverage */}
      {defensiveCoverage && (
        <SectionErrorBoundary label="Résistances défensives">
        <div className="rounded-xl bg-if-card border border-if-border-mid p-5 mb-4">
          <h2 className="text-sm font-semibold text-if-text-xs uppercase tracking-wider mb-3">
            Résistances défensives
          </h2>
          <p className="text-xs text-if-muted mb-3">
            Efficacité des types adverses sur cette fusion.
          </p>

          {(defensiveCoverage.quad.length > 0 || defensiveCoverage.double.length > 0) && (
            <div className="mb-3 space-y-2">
              {defensiveCoverage.quad.length > 0 && (
                <div>
                  <p className="text-xs font-medium mb-1.5" style={{ color: "#f87171" }}>
                    Faiblesse ×4 — {defensiveCoverage.quad.length} type{defensiveCoverage.quad.length > 1 ? "s" : ""}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {defensiveCoverage.quad.map((t) => <TypeBadge key={t} typeName={t} label={TYPE_FR[t] ?? t} size="sm" />)}
                  </div>
                </div>
              )}
              {defensiveCoverage.double.length > 0 && (
                <div>
                  <p className="text-xs font-medium mb-1.5" style={{ color: "#fb923c" }}>
                    Faiblesse ×2 — {defensiveCoverage.double.length} type{defensiveCoverage.double.length > 1 ? "s" : ""}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {defensiveCoverage.double.map((t) => <TypeBadge key={t} typeName={t} label={TYPE_FR[t] ?? t} size="sm" />)}
                  </div>
                </div>
              )}
            </div>
          )}

          {(defensiveCoverage.half.length > 0 || defensiveCoverage.quarter.length > 0) && (
            <div className="mb-3 space-y-2">
              {defensiveCoverage.quarter.length > 0 && (
                <div>
                  <p className="text-xs font-medium mb-1.5" style={{ color: "#34d399" }}>
                    Résistance ×¼ — {defensiveCoverage.quarter.length} type{defensiveCoverage.quarter.length > 1 ? "s" : ""}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {defensiveCoverage.quarter.map((t) => <TypeBadge key={t} typeName={t} label={TYPE_FR[t] ?? t} size="sm" />)}
                  </div>
                </div>
              )}
              {defensiveCoverage.half.length > 0 && (
                <div>
                  <p className="text-xs font-medium mb-1.5" style={{ color: "#4ade80" }}>
                    Résistance ×½ — {defensiveCoverage.half.length} type{defensiveCoverage.half.length > 1 ? "s" : ""}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {defensiveCoverage.half.map((t) => <TypeBadge key={t} typeName={t} label={TYPE_FR[t] ?? t} size="sm" />)}
                  </div>
                </div>
              )}
            </div>
          )}

          {defensiveCoverage.immune.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1.5" style={{ color: "#a78bfa" }}>
                Immunité ×0 — {defensiveCoverage.immune.length} type{defensiveCoverage.immune.length > 1 ? "s" : ""}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {defensiveCoverage.immune.map((t) => <TypeBadge key={t} typeName={t} label={TYPE_FR[t] ?? t} size="sm" />)}
              </div>
            </div>
          )}
        </div>
        </SectionErrorBoundary>
      )}

      {/* Moveset */}
      <SectionErrorBoundary label="Capacités">
      <div className="rounded-xl bg-if-card border border-if-border-mid p-5 mb-4">
        <h2 className="text-sm font-semibold text-if-text-xs uppercase tracking-wider mb-4">
          Capacités apprises
        </h2>
        {isLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 rounded bg-if-input" />
            ))}
          </div>
        ) : (
          <FusionMovesetTable
            moves={moves}
            expertMoves={expertMoves}
            headName={fusion.head_name_fr ?? fusion.head_name_en}
            bodyName={fusion.body_name_fr ?? fusion.body_name_en}
          />
        )}
      </div>
      </SectionErrorBoundary>

      <div className="flex flex-wrap gap-3">
        <AiSuggestButton
          pokemonName={fusionName}
          pokemonId={hId}
          context={aiContext}
          question={`Analyse cette fusion ${fusionName} dans Pokémon Infinite Fusion : potentiel compétitif, meilleur set (capacités, talent, objet), synergies d'équipe et comment la contrer.`}
        />
      </div>
    </div>
  );
}
