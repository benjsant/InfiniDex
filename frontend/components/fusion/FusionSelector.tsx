"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SearchBar } from "@/components/layout/SearchBar";
import { usePokemonSearch, usePokemonList } from "@/hooks/usePokemon";
import { getPokemon } from "@/lib/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import type { PokemonListItem } from "@/types/api";
import { basePokemonSprite } from "@/lib/constants";
import { primaryType, secondaryType } from "@/lib/utils";
import Image from "next/image";

interface PokemonPickerProps {
  label: string;
  selected: PokemonListItem | null;
  onSelect: (p: PokemonListItem) => void;
  loading?: boolean;
}

function PokemonPicker({ label, selected, onSelect, loading = false }: PokemonPickerProps) {
  const [q, setQ]       = useState("");
  const [open, setOpen] = useState(false);

  const searchQuery = usePokemonSearch(q, { enabled: open && q.trim().length >= 2 });
  const listQuery   = usePokemonList({ page_size: 20 }, { enabled: open });

  const results = q.trim().length >= 2
    ? (searchQuery.data ?? [])
    : (listQuery.data ?? []).slice(0, 20);

  const handleSelect = useCallback(
    (p: PokemonListItem) => {
      onSelect(p);
      setOpen(false);
      setQ("");
    },
    [onSelect],
  );

  const t1 = selected ? primaryType(selected.types) : null;
  const t2 = selected ? secondaryType(selected.types) : null;

  return (
    <div className="flex-1 relative">
      <p className="text-xs text-[rgb(120,120,140)] mb-1 font-semibold uppercase tracking-wider">
        {label}
      </p>

      {loading ? (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-[rgb(20,20,28)] border border-[rgb(50,50,70)] animate-pulse">
          <div className="w-12 h-12 rounded bg-[rgb(40,40,55)] shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 rounded bg-[rgb(40,40,55)]" />
            <div className="h-3 w-16 rounded bg-[rgb(40,40,55)]" />
          </div>
        </div>
      ) : selected ? (
        <div
          className="flex items-center gap-3 p-3 rounded-lg bg-[rgb(20,20,28)] border border-indigo-500 cursor-pointer hover:border-indigo-400 transition-colors"
          onClick={() => setOpen(!open)}
        >
          <Image
            src={basePokemonSprite(selected.national_id ?? selected.id)}
            alt={selected.name_en}
            width={48}
            height={48}
            unoptimized
            className="object-contain"
          />
          <div>
            <p className="font-semibold text-[rgb(220,220,255)]">{selected.name_en}</p>
            <div className="flex gap-1 mt-0.5">
              {t1 && <TypeBadge typeName={t1.name_en} size="sm" />}
              {t2 && <TypeBadge typeName={t2.name_en} size="sm" />}
            </div>
          </div>
          <span className="ml-auto text-xs text-[rgb(100,100,120)]">Changer</span>
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="w-full p-3 rounded-lg bg-[rgb(20,20,28)] border border-dashed border-[rgb(60,60,80)] text-[rgb(120,120,140)] hover:border-indigo-500 hover:text-indigo-300 transition-all"
        >
          + Choisir un Pokémon
        </button>
      )}

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 z-30 bg-[rgb(20,20,30)] border border-[rgb(50,50,70)] rounded-lg shadow-xl">
          <div className="p-2">
            <SearchBar onSearch={setQ} placeholder="Rechercher…" className="text-sm" />
          </div>
          <div className="max-h-64 overflow-y-auto">
            {results.map((p) => {
              const pt1 = primaryType(p.types);
              const pt2 = secondaryType(p.types);
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelect(p)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[rgb(30,30,45)] transition-colors text-left"
                >
                  <span className="text-xs text-[rgb(100,100,120)] w-8">#{p.id}</span>
                  <span className="text-sm text-[rgb(220,220,255)]">{p.name_en}</span>
                  <div className="ml-auto flex gap-1">
                    {pt1 && <TypeBadge typeName={pt1.name_en} size="sm" />}
                    {pt2 && <TypeBadge typeName={pt2.name_en} size="sm" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function FusionSelector() {
  const [head, setHead] = useState<PokemonListItem | null>(null);
  const [body, setBody] = useState<PokemonListItem | null>(null);
  const [preloading, setPreloading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Pre-select from URL params (?head=ID&?body=ID) — e.g. links from Pokédex page.
  useEffect(() => {
    const headId = searchParams.get("head");
    const bodyId = searchParams.get("body");
    if (!headId && !bodyId) return;
    setPreloading(true);
    Promise.all([
      headId ? getPokemon(parseInt(headId, 10)).then(setHead).catch(() => null) : Promise.resolve(),
      bodyId ? getPokemon(parseInt(bodyId, 10)).then(setBody).catch(() => null) : Promise.resolve(),
    ]).finally(() => setPreloading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const canFuse = head != null && body != null;

  const handleFuse = () => {
    if (!head || !body) return;
    router.push(`/fusion/${head.id}/${body.id}`);
  };

  const handleSwap = () => {
    setHead(body);
    setBody(head);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4 items-start">
        <PokemonPicker label="Tête (Head)" selected={head} onSelect={setHead} loading={preloading} />
        <button
          onClick={handleSwap}
          disabled={!head && !body}
          className="self-center mt-5 p-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] hover:text-white hover:border-indigo-500 disabled:opacity-40 transition-all"
          title="Inverser tête/corps"
        >
          ⇄
        </button>
        <PokemonPicker label="Corps (Body)" selected={body} onSelect={setBody} loading={preloading} />
      </div>

      <button
        onClick={handleFuse}
        disabled={!canFuse}
        className="w-full py-3 rounded-lg font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white"
      >
        {canFuse
          ? `⚗️ Fusionner ${head!.name_en} + ${body!.name_en}`
          : "Sélectionne deux Pokémon"}
      </button>
    </div>
  );
}
