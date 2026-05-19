"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { GitCompare, X, Search, ChevronRight, ArrowUpDown } from "lucide-react";
import { useFusion } from "@/hooks/useFusion";
import { usePokemonSearch } from "@/hooks/usePokemon";
import { FusionSprite } from "@/components/fusion/FusionSprite";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import type { FusionResult, PokemonListItem } from "@/types/api";

const STAT_KEYS: { key: keyof FusionResult; label: string }[] = [
  { key: "hp",         label: "HP"     },
  { key: "attack",     label: "Atk"    },
  { key: "defense",    label: "Déf"    },
  { key: "sp_attack",  label: "AtkSpé" },
  { key: "sp_defense", label: "DéfSpé" },
  { key: "speed",      label: "Vit"    },
];

function PokemonCombobox({
  label,
  value,
  onChange,
}: {
  label: string;
  value: PokemonListItem | null;
  onChange: (p: PokemonListItem | null) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data: results = [] } = usePokemonSearch(q.length >= 2 ? q : "", { enabled: q.length >= 2 });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (value) {
    return (
      <div className="flex items-center justify-between px-3 py-2 rounded-lg" style={{ background: "var(--color-if-card)", border: "1px solid #e8b84b44" }}>
        <span className="text-sm" style={{ color: "var(--color-if-text)" }}>
          <span className="text-xs mr-2" style={{ color: "var(--color-if-muted)" }}>#{String(value.id).padStart(3, "0")}</span>
          {value.name_fr ?? value.name_en}
        </span>
        <button onClick={() => { onChange(null); setQ(""); }} style={{ color: "var(--color-if-muted)" }}>
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: "var(--color-if-bg)", border: "1px solid var(--color-if-border)" }}>
        <Search size={13} style={{ color: "var(--color-if-muted)", flexShrink: 0 }} />
        <input
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-if-text-lo"
          style={{ color: "var(--color-if-text)" }}
          placeholder={label}
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open && results.length > 0 && (
        <div
          className="absolute z-50 w-full mt-1 rounded-lg overflow-hidden shadow-xl max-h-52 overflow-y-auto"
          style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
        >
          {results.slice(0, 12).map((p) => (
            <button
              key={p.id}
              className="w-full text-left px-3 py-2 text-sm transition-colors hover:bg-if-border"
              style={{ color: "var(--color-if-text)" }}
              onMouseDown={(e) => { e.preventDefault(); onChange(p); setQ(""); setOpen(false); }}
            >
              <span className="text-xs mr-2" style={{ color: "var(--color-if-muted)" }}>#{String(p.id).padStart(3, "0")}</span>
              {p.name_fr ?? p.name_en}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SlotSelector({
  slotLabel,
  head,
  body,
  onHead,
  onBody,
  onClear,
  onSwap,
}: {
  slotLabel: string;
  head: PokemonListItem | null;
  body: PokemonListItem | null;
  onHead: (p: PokemonListItem | null) => void;
  onBody: (p: PokemonListItem | null) => void;
  onClear: () => void;
  onSwap: () => void;
}) {
  return (
    <div className="rounded-xl p-4 space-y-3" style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-if-muted)" }}>{slotLabel}</p>
        <div className="flex items-center gap-2">
          {head && body && (
            <button
              onClick={onSwap}
              title="Intervertir tête et corps"
              className="flex items-center gap-1 text-xs px-2 py-0.5 rounded transition-colors hover:opacity-80"
              style={{ color: "var(--color-if-text-lo)", background: "var(--color-if-elevated)", border: "1px solid var(--color-if-border-mid)" }}
            >
              <ArrowUpDown size={11} />
              Inverser
            </button>
          )}
          {(head || body) && (
            <button onClick={onClear} className="text-xs" style={{ color: "var(--color-if-text-lo)" }}>
              <X size={12} className="inline" /> Effacer
            </button>
          )}
        </div>
      </div>
      <div className="space-y-2">
        <PokemonCombobox label="Pokémon tête…" value={head} onChange={onHead} />
        <PokemonCombobox label="Pokémon corps…" value={body} onChange={onBody} />
      </div>
      {head && body && (
        <div className="flex items-center justify-center pt-1">
          <FusionSprite headId={head.id} bodyId={body.id} size={80} />
        </div>
      )}
    </div>
  );
}

function StatRow({ label, a, b }: { label: string; a: number; b: number }) {
  const max = Math.max(a, b, 1);
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 py-1.5">
      <div className="flex items-center justify-end gap-2">
        <span className="text-sm font-mono font-bold w-8 text-right" style={{ color: a > b ? "#4ade80" : "var(--color-if-text-dim)" }}>{a}</span>
        <div className="h-2 rounded-full flex-1 max-w-[80px]" style={{ background: "var(--color-if-border)" }}>
          <div className="h-full rounded-full ml-auto" style={{ width: `${Math.round((a / max) * 100)}%`, background: a > b ? "#4ade80" : "#6366f1" }} />
        </div>
      </div>
      <span className="text-xs text-center w-14 shrink-0" style={{ color: "var(--color-if-muted)" }}>{label}</span>
      <div className="flex items-center gap-2">
        <div className="h-2 rounded-full flex-1 max-w-[80px]" style={{ background: "var(--color-if-border)" }}>
          <div className="h-full rounded-full" style={{ width: `${Math.round((b / max) * 100)}%`, background: b > a ? "#4ade80" : "#6366f1" }} />
        </div>
        <span className="text-sm font-mono font-bold w-8" style={{ color: b > a ? "#4ade80" : "var(--color-if-text-dim)" }}>{b}</span>
      </div>
    </div>
  );
}

function FusionHeader({ fusion }: { fusion: FusionResult }) {
  const total = STAT_KEYS.reduce((s, { key }) => s + (fusion[key] as number), 0);
  return (
    <div className="flex flex-col items-center gap-2">
      <Link href={`/fusion/${fusion.head_id}/${fusion.body_id}`} className="hover:opacity-80 transition-opacity">
        <div className="w-24 h-24 flex items-center justify-center rounded-xl" style={{ background: "var(--color-if-bg)", border: "1px solid var(--color-if-border)" }}>
          <FusionSprite headId={fusion.head_id} bodyId={fusion.body_id} size={88} />
        </div>
      </Link>
      <div className="text-center">
        <p className="text-xs font-semibold" style={{ color: "var(--color-if-text)" }}>
          {fusion.head_name_fr ?? fusion.head_name_en}/{fusion.body_name_fr ?? fusion.body_name_en}
        </p>
        <div className="flex gap-1 justify-center mt-1">
          {fusion.type1 && <TypeBadge typeName={fusion.type1.name_en} label={fusion.type1.name_fr ?? fusion.type1.name_en} size="sm" />}
          {fusion.type2 && <TypeBadge typeName={fusion.type2.name_en} label={fusion.type2.name_fr ?? fusion.type2.name_en} size="sm" />}
        </div>
        <p className="text-xs mt-1" style={{ color: "var(--color-if-muted)" }}>BST <span className="font-mono font-bold" style={{ color: "var(--color-if-text-dim)" }}>{total}</span></p>
      </div>
    </div>
  );
}

function CompareResult({
  headA, bodyA, headB, bodyB,
}: {
  headA: PokemonListItem; bodyA: PokemonListItem;
  headB: PokemonListItem; bodyB: PokemonListItem;
}) {
  const { data: fusionA, isLoading: la } = useFusion(headA.id, bodyA.id);
  const { data: fusionB, isLoading: lb } = useFusion(headB.id, bodyB.id);

  if (la || lb) return <div className="animate-pulse h-48 rounded-xl bg-if-card" />;
  if (!fusionA || !fusionB) return <p className="text-center py-8" style={{ color: "var(--color-if-muted)" }}>Erreur de chargement.</p>;

  const totalA = STAT_KEYS.reduce((s, { key }) => s + (fusionA[key] as number), 0);
  const totalB = STAT_KEYS.reduce((s, { key }) => s + (fusionB[key] as number), 0);

  return (
    <div className="space-y-4 mt-6">
      {/* Sprite + name + types */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
        <FusionHeader fusion={fusionA} />
        <span className="text-lg font-bold" style={{ color: "var(--color-if-border-hi)" }}>VS</span>
        <FusionHeader fusion={fusionB} />
      </div>

      {/* Stats */}
      <div className="rounded-xl p-4" style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-if-muted)" }}>Statistiques</p>
        <div className="divide-y" style={{ borderColor: "var(--color-if-border-lo)" }}>
          {STAT_KEYS.map(({ key, label }) => (
            <StatRow key={key} label={label} a={fusionA[key] as number} b={fusionB[key] as number} />
          ))}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 pt-3 mt-1 border-t" style={{ borderColor: "var(--color-if-border)" }}>
          <span className="text-sm font-bold font-mono text-right" style={{ color: totalA > totalB ? "#4ade80" : "var(--color-if-text-dim)" }}>{totalA}</span>
          <span className="text-xs text-center w-14" style={{ color: "var(--color-if-muted)" }}>Total</span>
          <span className="text-sm font-bold font-mono" style={{ color: totalB > totalA ? "#4ade80" : "var(--color-if-text-dim)" }}>{totalB}</span>
        </div>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [headA, setHeadA] = useState<PokemonListItem | null>(null);
  const [bodyA, setBodyA] = useState<PokemonListItem | null>(null);
  const [headB, setHeadB] = useState<PokemonListItem | null>(null);
  const [bodyB, setBodyB] = useState<PokemonListItem | null>(null);

  const readyA = headA && bodyA;
  const readyB = headB && bodyB;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 mb-6">
        <GitCompare size={20} style={{ color: "#e8b84b" }} />
        <h1 className="text-xl font-bold" style={{ color: "var(--color-if-text)" }}>Comparateur de fusions</h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SlotSelector
          slotLabel="Fusion A"
          head={headA} body={bodyA}
          onHead={setHeadA} onBody={setBodyA}
          onClear={() => { setHeadA(null); setBodyA(null); }}
          onSwap={() => { setHeadA(bodyA); setBodyA(headA); }}
        />
        <SlotSelector
          slotLabel="Fusion B"
          head={headB} body={bodyB}
          onHead={setHeadB} onBody={setBodyB}
          onClear={() => { setHeadB(null); setBodyB(null); }}
          onSwap={() => { setHeadB(bodyB); setBodyB(headB); }}
        />
      </div>

      {readyA && readyB ? (
        <CompareResult headA={headA} bodyA={bodyA} headB={headB} bodyB={bodyB} />
      ) : (
        <div className="mt-8 flex items-center gap-3 text-sm" style={{ color: "var(--color-if-text-lo)" }}>
          <ChevronRight size={14} />
          {!readyA && !readyB
            ? "Choisis un Pokémon tête + corps pour chaque fusion."
            : !readyA
            ? "Complète la fusion A (tête et corps)."
            : "Complète la fusion B (tête et corps)."}
        </div>
      )}
    </div>
  );
}
