"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ArrowLeftRight, Star, GitCompare, Link2, Check } from "lucide-react";
import { useFusion, useFusionMoves, useFusionExpertMoves, useSprites } from "@/hooks/useFusion";
import { useHistory } from "@/hooks/useHistory";
import { useFavorites } from "@/hooks/useFavorites";
import { useComparison } from "@/hooks/useComparison";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { StatBar } from "@/components/pokemon/StatBar";
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

  const { data: fusion, isLoading, error }                   = useFusion(hId, bId);
  const { data: moves = [], isLoading: movesLoading }        = useFusionMoves(hId, bId);
  const { data: expertMoves = [], isLoading: expertLoading } = useFusionExpertMoves(hId, bId);
  const { data: sprites = [] }                               = useSprites(hId, bId);
  const { data: spritesReversed = [] }                       = useSprites(bId, hId);
  const { addEntry }                                         = useHistory();
  const { isFavorite, toggleFavorite }                       = useFavorites();
  const { isInComparison, addToComparison, canCompare }      = useComparison();

  useEffect(() => {
    if (fusion) {
      addEntry({
        headId: hId,
        bodyId: bId,
        headName: fusion.head_name_en,
        bodyName: fusion.body_name_en,
      });
    }
  // addEntry is stable (useCallback), fusion identity changes only when data arrives
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fusion]);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 animate-pulse space-y-4">
        <div className="h-8 w-64 bg-[rgb(30,30,42)] rounded" />
        <div className="h-48 w-48 bg-[rgb(30,30,42)] rounded-xl mx-auto" />
      </div>
    );
  }

  if (error || !fusion) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <p className="text-[rgb(120,120,140)]">Fusion introuvable.</p>
        <Link href="/fusion" className="mt-4 block transition-colors" style={{ color: "#e8b84b" }}>
          <ChevronLeft size={14} className="inline" /> Retour au calculateur
        </Link>
      </div>
    );
  }

  const fusionName = `${fusion.head_name_en}/${fusion.body_name_en}`;
  const reversedName = `${fusion.body_name_en}/${fusion.head_name_en}`;

  const stats = [
    { key: "hp",         value: fusion.hp },
    { key: "attack",     value: fusion.attack },
    { key: "defense",    value: fusion.defense },
    { key: "sp_attack",  value: fusion.sp_attack },
    { key: "sp_defense", value: fusion.sp_defense },
    { key: "speed",      value: fusion.speed },
  ];

  const baseTotal = stats.reduce((s, st) => s + st.value, 0);

  const [copied, setCopied] = useState(false);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const favorited   = isFavorite(hId, bId);
  const inComparison = isInComparison(hId, bId);

  const handleToggleFavorite = () =>
    toggleFavorite({ headId: hId, bodyId: bId, headName: fusion.head_name_en, bodyName: fusion.body_name_en });

  const handleAddToComparison = () =>
    addToComparison({ headId: hId, bodyId: bId, headName: fusion.head_name_en, bodyName: fusion.body_name_en });

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 text-sm text-[rgb(120,120,140)]">
          <Link href="/fusion" className="transition-colors hover:text-[#e8b84b]">Fusion</Link>
          <span>/</span>
          <span className="text-[rgb(200,200,220)]">{fusionName}</span>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyLink}
            title="Copier le lien"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: copied ? "rgba(74,222,128,0.12)" : "#111428",
              border: `1px solid ${copied ? "#4ade8066" : "#1e2240"}`,
              color: copied ? "#4ade80" : "#6b7199",
            }}
          >
            {copied ? <Check size={13} /> : <Link2 size={13} />}
            {copied ? "Copié !" : "Lien"}
          </button>
          <button
            onClick={handleToggleFavorite}
            title={favorited ? "Retirer des favoris" : "Ajouter aux favoris"}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: favorited ? "rgba(232,184,75,0.15)" : "#111428",
              border: `1px solid ${favorited ? "#e8b84b66" : "#1e2240"}`,
              color: favorited ? "#e8b84b" : "#6b7199",
            }}
          >
            <Star size={13} fill={favorited ? "currentColor" : "none"} />
            {favorited ? "Favori" : "Favori"}
          </button>

          {inComparison ? (
            <Link
              href="/fusion/compare"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all"
              style={{
                background: "rgba(99,102,241,0.15)",
                border: "1px solid #6366f166",
                color: "#818cf8",
              }}
            >
              <GitCompare size={13} />
              {canCompare ? "Comparer →" : "Dans la sélection"}
            </Link>
          ) : (
            <button
              onClick={handleAddToComparison}
              title="Ajouter à la comparaison"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:border-indigo-500/60 hover:text-indigo-300"
              style={{ background: "#111428", border: "1px solid #1e2240", color: "#6b7199" }}
            >
              <GitCompare size={13} />
              Comparer
            </button>
          )}
        </div>
      </div>

      {/* Main card */}
      <div className="rounded-xl p-4 sm:p-6 mb-6" style={{ background: "#111428", border: "1px solid #1e2240" }}>
        {/* Sprites row */}
        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start mb-6">
          {/* Normal sprite — carrousel si plusieurs variants */}
          <div className="flex flex-col items-center gap-1">
            <SpriteCarousel headId={hId} bodyId={bId} sprites={sprites} size={128} />
            <p className="text-xs font-medium" style={{ color: "#8c8ca0" }}>{fusionName}</p>
          </div>

          <div className="hidden sm:flex items-center self-center text-[rgb(60,60,80)]"><ArrowLeftRight size={20} /></div>

          {/* Reversed sprite */}
          <Link href={`/fusion/${bId}/${hId}`} className="group opacity-70 hover:opacity-100 transition-opacity">
            <div className="flex flex-col items-center gap-1">
              <SpriteCarousel headId={bId} bodyId={hId} sprites={spritesReversed} size={128} />
              <p className="text-xs font-medium" style={{ color: "#8c8ca0" }}>{reversedName}</p>
            </div>
          </Link>
        </div>

        {/* Name + types */}
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-[rgb(220,220,255)] mb-1">{fusionName}</h1>
          <div className="flex gap-2 justify-center sm:justify-start mb-1 text-xs text-[rgb(120,120,140)]">
            <span>
              Tête :{" "}
              <Link href={`/pokedex/${hId}`} className="transition-colors" style={{ color: "#e8b84b" }}>
                {fusion.head_name_en} #{hId}
              </Link>
            </span>
            <span style={{ color: "#2d3260" }}>·</span>
            <span>
              Corps :{" "}
              <Link href={`/pokedex/${bId}`} className="transition-colors" style={{ color: "#e8b84b" }}>
                {fusion.body_name_en} #{bId}
              </Link>
            </span>
          </div>
          <div className="flex gap-2 justify-center sm:justify-start">
            {fusion.type1 && <TypeBadge typeName={fusion.type1.name_en} />}
            {fusion.type2 && <TypeBadge typeName={fusion.type2.name_en} />}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="rounded-xl bg-[rgb(20,20,28)] border border-[rgb(50,50,70)] p-5 mb-4">
        <h2 className="text-sm font-semibold text-[rgb(120,120,140)] uppercase tracking-wider mb-4">
          Statistiques fusionnées
        </h2>
        <div className="space-y-3 max-w-md">
          {stats.map(({ key, value }) => (
            <StatBar key={key} stat={key} value={value} />
          ))}
          <div className="flex items-center gap-3 pt-2 border-t border-[rgb(40,40,55)]">
            <span className="w-24 text-right text-xs text-[rgb(120,120,140)]">Total</span>
            <span className="text-sm font-bold font-mono text-[rgb(220,220,255)]">{baseTotal}</span>
          </div>
        </div>
        <p className="text-xs text-[rgb(80,80,100)] mt-4">
          Physique (HP/Atk/Déf/Vit) = ⌊Body×⅔ + Head×⅓⌋ · Spécial (AtkSpé/DéfSpé) = ⌊Head×⅔ + Body×⅓⌋
        </p>
      </div>

      {/* Moveset */}
      <div className="rounded-xl bg-[rgb(20,20,28)] border border-[rgb(50,50,70)] p-5 mb-4">
        <h2 className="text-sm font-semibold text-[rgb(120,120,140)] uppercase tracking-wider mb-4">
          Capacités apprises
        </h2>
        {movesLoading || expertLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 rounded bg-[rgb(30,30,42)]" />
            ))}
          </div>
        ) : (
          <FusionMovesetTable
            moves={moves}
            expertMoves={expertMoves}
            headName={fusion.head_name_en}
            bodyName={fusion.body_name_en}
          />
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <AiSuggestButton
          pokemonName={fusionName}
          pokemonId={hId}
          context={`Fusion de ${fusion.head_name_en} (tête) et ${fusion.body_name_en} (corps). Types: ${fusion.type1?.name_en ?? "?"}${fusion.type2 ? "/" + fusion.type2.name_en : ""}. Total: ${baseTotal}.`}
        />
      </div>
    </div>
  );
}

