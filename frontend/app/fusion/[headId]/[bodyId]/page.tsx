"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, ArrowLeftRight } from "lucide-react";
import { useFusion, useFusionMoves, useFusionExpertMoves, useSprites } from "@/hooks/useFusion";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { StatBar } from "@/components/pokemon/StatBar";
import { AiSuggestButton } from "@/components/ai/AiSuggestButton";
import { FusionSprite } from "@/components/fusion/FusionSprite";
import { FusionMovesetTable } from "@/components/fusion/FusionMovesetTable";
import { CreatorBadge } from "@/components/fusion/CreatorModal";

export default function FusionResultPage({
  params,
}: {
  params: Promise<{ headId: string; bodyId: string }>;
}) {
  const { headId, bodyId } = use(params);
  const hId = parseInt(headId, 10);
  const bId = parseInt(bodyId, 10);

  const { data: fusion, isLoading, error }          = useFusion(hId, bId);
  const { data: moves = [], isLoading: movesLoading }       = useFusionMoves(hId, bId);
  const { data: expertMoves = [], isLoading: expertLoading } = useFusionExpertMoves(hId, bId);
  const { data: sprites = [] }                              = useSprites(hId, bId);
  const { data: spritesReversed = [] }                      = useSprites(bId, hId);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 animate-pulse space-y-4">
        <div className="h-8 w-64 bg-if-input rounded" />
        <div className="h-48 w-48 bg-if-input rounded-xl mx-auto" />
      </div>
    );
  }

  if (error || !fusion) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <p className="text-if-text-xs">Fusion introuvable.</p>
        <Link href="/fusion" className="mt-4 block transition-colors" style={{ color: "var(--color-if-accent)" }}>
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

  const defaultSprite   = sprites.find((s) => s.is_default) ?? sprites[0];
  const defaultReversed = spritesReversed.find((s) => s.is_default) ?? spritesReversed[0];

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 text-sm text-if-text-xs mb-6">
        <Link href="/fusion" className="transition-colors hover:text-[#e8b84b]">Fusion</Link>
        <span>/</span>
        <span className="text-if-text-dim">{fusionName}</span>
      </div>

      {/* Main card */}
      <div className="rounded-xl p-4 sm:p-6 mb-6" style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}>
        {/* Sprites row */}
        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start mb-6">
          {/* Normal sprite */}
          <SpriteCard
            headId={hId}
            bodyId={bId}
            label={fusionName}
            creators={defaultSprite?.creators ?? []}
          />

          <div className="hidden sm:flex items-center self-center text-if-border-hi"><ArrowLeftRight size={20} /></div>

          {/* Reversed sprite */}
          <Link href={`/fusion/${bId}/${hId}`} className="group">
            <SpriteCard
              headId={bId}
              bodyId={hId}
              label={reversedName}
              creators={defaultReversed?.creators ?? []}
              muted
            />
          </Link>
        </div>

        {/* Name + types */}
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-if-text-hi mb-1">{fusionName}</h1>
          <div className="flex gap-2 justify-center sm:justify-start mb-1 text-xs text-if-text-xs">
            <span>
              Tête :{" "}
              <Link href={`/pokedex/${hId}`} className="transition-colors" style={{ color: "var(--color-if-accent)" }}>
                {fusion.head_name_en} #{hId}
              </Link>
            </span>
            <span style={{ color: "var(--color-if-border-hi)" }}>·</span>
            <span>
              Corps :{" "}
              <Link href={`/pokedex/${bId}`} className="transition-colors" style={{ color: "var(--color-if-accent)" }}>
                {fusion.body_name_en} #{bId}
              </Link>
            </span>
          </div>
          <div className="flex gap-2 justify-center sm:justify-start">
            <TypeBadge typeName={fusion.type1.name_en} />
            {fusion.type2 && <TypeBadge typeName={fusion.type2.name_en} />}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="rounded-xl bg-if-deep border border-if-border-mid p-5 mb-4">
        <h2 className="text-sm font-semibold text-if-text-xs uppercase tracking-wider mb-4">
          Statistiques fusionnées
        </h2>
        <div className="space-y-3 max-w-md">
          {stats.map(({ key, value }) => (
            <StatBar key={key} stat={key} value={value} />
          ))}
          <div className="flex items-center gap-3 pt-2 border-t border-if-border-lo">
            <span className="w-24 text-right text-xs text-if-text-xs">Total</span>
            <span className="text-sm font-bold font-mono text-if-text-hi">{baseTotal}</span>
          </div>
        </div>
        <p className="text-xs text-if-muted mt-4">
          Physique (HP/Atk/Déf/Vit) = ⌊Body×⅔ + Head×⅓⌋ · Spécial (AtkSpé/DéfSpé) = ⌊Head×⅔ + Body×⅓⌋
        </p>
      </div>

      {/* Moveset */}
      <div className="rounded-xl bg-if-deep border border-if-border-mid p-5 mb-4">
        <h2 className="text-sm font-semibold text-if-text-xs uppercase tracking-wider mb-4">
          Capacités apprises
        </h2>
        {movesLoading || expertLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 rounded bg-if-input" />
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
          context={`Fusion de ${fusion.head_name_en} (tête) et ${fusion.body_name_en} (corps). Types: ${fusion.type1.name_en}${fusion.type2 ? "/" + fusion.type2.name_en : ""}. Total: ${baseTotal}.`}
        />
      </div>
    </div>
  );
}

function SpriteCard({
  headId,
  bodyId,
  label,
  creators,
  muted = false,
}: {
  headId: number;
  bodyId: number;
  label: string;
  creators: string[];
  muted?: boolean;
}) {
  return (
    <div className={`flex flex-col items-center gap-2 ${muted ? "opacity-70 hover:opacity-100 transition-opacity" : ""}`}>
      <div className="w-32 h-32 sm:w-40 sm:h-40 flex items-center justify-center rounded-xl shrink-0" style={{ background: "var(--color-if-bg)", border: "1px solid var(--color-if-border)" }}>
        <FusionSprite headId={headId} bodyId={bodyId} size={128} />
      </div>
      <p className="text-xs text-if-text-xs font-medium">{label}</p>
      {creators.length > 0 ? (
        <p className="text-[10px] text-if-muted text-center leading-tight">
          par{" "}
          {creators.map((c, i) => (
            <span key={c}>
              {i > 0 && ", "}
              <CreatorBadge name={c} />
            </span>
          ))}
        </p>
      ) : (
        <p className="text-[10px] text-if-muted italic">Auto-généré</p>
      )}
    </div>
  );
}
