"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeftRight } from "lucide-react";
import { usePokemonList } from "@/hooks/usePokemon";
import { getPokemon } from "@/lib/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import type { PokemonListItem } from "@/types/api";
import { basePokemonSprite } from "@/lib/constants";
import { primaryType, secondaryType, normalize } from "@/lib/utils";
import Image from "next/image";

type GameFilter = "kanto" | "hoenn" | "all";

const PARAMS_BY_GAME: Record<GameFilter, { page_size: number; include_hoenn: boolean }> = {
  kanto: { page_size: 600, include_hoenn: false },
  hoenn: { page_size: 600, include_hoenn: true },
  all:   { page_size: 600, include_hoenn: true },
};

interface PokemonPickerProps {
  label: string;
  selected: PokemonListItem | null;
  onSelect: (p: PokemonListItem) => void;
  game: GameFilter;
  loading?: boolean;
}

function PokemonPicker({ label, selected, onSelect, game, loading = false }: PokemonPickerProps) {
  const [q, setQ]       = useState("");
  const [open, setOpen] = useState(false);
  const inputRef        = useRef<HTMLInputElement>(null);

  const { data: rawList = [], isError: listError } = usePokemonList(PARAMS_BY_GAME[game]);

  const allPokemon = useMemo(() => {
    if (game === "hoenn") return rawList.filter((p) => p.is_hoenn_only);
    return rawList;
  }, [rawList, game]);

  const results = useMemo(() => {
    const needle = normalize(q);
    if (needle.length < 1) return allPokemon;
    return allPokemon.filter(
      (p) =>
        normalize(p.name_en).includes(needle) ||
        (p.name_fr && normalize(p.name_fr).includes(needle)),
    );
  }, [allPokemon, q]);

  const handleOpen = useCallback(() => {
    setOpen(true);
    // Focus the search input on next frame after render
    setTimeout(() => inputRef.current?.focus(), 0);
  }, []);

  const handleSelect = useCallback(
    (p: PokemonListItem) => {
      onSelect(p);
      setOpen(false);
      setQ("");
    },
    [onSelect],
  );

  // Close on outside click
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQ("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const t1 = selected ? primaryType(selected.types) : null;
  const t2 = selected ? secondaryType(selected.types) : null;

  return (
    <div className="flex-1 relative" ref={containerRef}>
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
          onClick={handleOpen}
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
            <p className="font-semibold text-[rgb(220,220,255)]">{selected.name_fr ?? selected.name_en}</p>
            <div className="flex gap-1 mt-0.5">
              {t1 && <TypeBadge typeName={t1.name_en} label={t1.name_fr ?? t1.name_en} size="sm" />}
              {t2 && <TypeBadge typeName={t2.name_en} label={t2.name_fr ?? t2.name_en} size="sm" />}
            </div>
          </div>
          <span className="ml-auto text-xs text-[rgb(100,100,120)]">Changer</span>
        </div>
      ) : (
        <button
          onClick={handleOpen}
          className="w-full p-3 rounded-lg bg-[rgb(20,20,28)] border border-dashed border-[rgb(60,60,80)] text-[rgb(120,120,140)] hover:border-indigo-500 hover:text-indigo-300 transition-all"
        >
          + Choisir un Pokémon
        </button>
      )}

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 z-30 bg-[rgb(20,20,30)] border border-[rgb(50,50,70)] rounded-lg shadow-xl">
          {listError ? (
            <p className="px-4 py-6 text-sm text-center text-red-400">
              Impossible de charger la liste — vérifie ta connexion.
            </p>
          ) : (
          <>
          <div className="p-2 border-b border-[rgb(40,40,55)]">
            <input
              ref={inputRef}
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Rechercher par nom (FR ou EN)…"
              className="w-full px-3 py-1.5 rounded bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(220,220,255)] placeholder:text-[rgb(100,100,120)] focus:outline-none focus:border-indigo-500 text-sm transition-colors"
            />
            <p className="text-[10px] text-[rgb(80,80,100)] mt-1 px-1">
              {results.length} / {allPokemon.length} Pokémon
            </p>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {results.map((p) => {
              const pt1 = primaryType(p.types);
              const pt2 = secondaryType(p.types);
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelect(p)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[rgb(30,30,45)] transition-colors text-left"
                >
                  <span className="text-xs text-[rgb(80,80,100)] w-8 shrink-0">#{p.id}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-[rgb(220,220,255)]">{p.name_fr ?? p.name_en}</span>
                    {p.name_fr && (
                      <span className="ml-1 text-xs text-[rgb(100,100,120)]">{p.name_en}</span>
                    )}
                  </div>
                  <div className="ml-auto flex gap-1 shrink-0">
                    {pt1 && <TypeBadge typeName={pt1.name_en} label={pt1.name_fr ?? pt1.name_en} size="sm" />}
                    {pt2 && <TypeBadge typeName={pt2.name_en} label={pt2.name_fr ?? pt2.name_en} size="sm" />}
                  </div>
                </button>
              );
            })}
          </div>
          </>
          )}
        </div>
      )}
    </div>
  );
}

export function FusionSelector() {
  const [head, setHead] = useState<PokemonListItem | null>(null);
  const [body, setBody] = useState<PokemonListItem | null>(null);
  const [game, setGame] = useState<GameFilter>("kanto");
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
      <div className="flex items-center justify-between">
        <p className="text-xs text-[rgb(100,100,120)] uppercase tracking-wider font-semibold">Pokédex</p>
        <div className="flex rounded-lg overflow-hidden border border-[rgb(50,50,70)] text-xs font-semibold">
          {(["kanto", "hoenn", "all"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setGame(v)}
              className={`px-2.5 py-1 transition-colors ${game === v ? "bg-indigo-600 text-white" : "bg-[rgb(25,25,38)] text-[rgb(140,140,170)] hover:bg-[rgb(35,35,50)]"}`}
            >
              {v === "kanto" ? "IF Kanto" : v === "hoenn" ? "IF Hoenn" : "Tous"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-start">
        <PokemonPicker label="Tête (Head)" selected={head} onSelect={setHead} game={game} loading={preloading} />
        <button
          onClick={handleSwap}
          disabled={!head && !body}
          className="self-center mt-5 p-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] hover:text-white hover:border-indigo-500 disabled:opacity-40 transition-all"
          title="Inverser tête/corps"
        >
          <ArrowLeftRight size={16} />
        </button>
        <PokemonPicker label="Corps (Body)" selected={body} onSelect={setBody} game={game} loading={preloading} />
      </div>

      <button
        onClick={handleFuse}
        disabled={!canFuse}
        className="w-full py-3 rounded-lg font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white"
      >
        {canFuse
          ? `Fusionner ${head!.name_fr ?? head!.name_en} + ${body!.name_fr ?? body!.name_en}`
          : "Sélectionne deux Pokémon"}
      </button>
    </div>
  );
}
