"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, BookOpen, Zap, Star } from "lucide-react";
import { searchPokemon, searchMoves, searchAbilities } from "@/lib/api";
import type { PokemonListItem, MoveListItem, AbilityListItem } from "@/types/api";

interface Results {
  pokemon:   PokemonListItem[];
  moves:     MoveListItem[];
  abilities: AbilityListItem[];
}

const EMPTY: Results = { pokemon: [], moves: [], abilities: [] };
const MAX_PER_SECTION = 4;
// Minimum query length before firing requests
const MIN_Q = 2;

export function GlobalSearch() {
  const router = useRouter();
  const [open, setOpen]       = useState(false);
  const [q, setQ]             = useState("");
  const [results, setResults] = useState<Results>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [cursor, setCursor]   = useState(-1);

  const inputRef   = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Keyboard shortcut: Ctrl+K / Cmd+K ────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Focus input when overlay opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQ("");
      setResults(EMPTY);
      setCursor(-1);
    }
  }, [open]);

  // ── Debounced search ──────────────────────────────────────────────────────
  const search = useCallback((value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < MIN_Q) { setResults(EMPTY); setLoading(false); return; }

    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      const [pokemon, moves, abilities] = await Promise.allSettled([
        searchPokemon(value),
        searchMoves(value),
        searchAbilities(value),
      ]);
      setResults({
        pokemon:   pokemon.status   === "fulfilled" ? pokemon.value.slice(0, MAX_PER_SECTION)   : [],
        moves:     moves.status     === "fulfilled" ? moves.value.slice(0, MAX_PER_SECTION)     : [],
        abilities: abilities.status === "fulfilled" ? abilities.value.slice(0, MAX_PER_SECTION) : [],
      });
      setLoading(false);
      setCursor(-1);
    }, 220);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQ(e.target.value);
    search(e.target.value);
  };

  // ── Flat list of navigable items for keyboard nav ─────────────────────────
  const items: { href: string; label: string }[] = [
    ...results.pokemon.map(  (p) => ({ href: `/pokedex/${p.id}`,    label: p.name_fr ?? p.name_en })),
    ...results.moves.map(    (m) => ({ href: `/moves/${m.id}`,      label: m.name_fr ?? m.name_en })),
    ...results.abilities.map((a) => ({ href: `/abilities/${a.id}`,  label: a.name_fr ?? a.name_en })),
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, items.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setCursor((c) => Math.max(c - 1, -1)); }
    if (e.key === "Enter" && cursor >= 0 && items[cursor]) {
      router.push(items[cursor].href);
      setOpen(false);
    }
    if (e.key === "Enter" && cursor === -1 && results.pokemon.length > 0) {
      router.push(`/pokedex/${results.pokemon[0].id}`);
      setOpen(false);
    }
  };

  const navigate = (href: string) => { router.push(href); setOpen(false); };

  const hasResults = results.pokemon.length > 0 || results.moves.length > 0 || results.abilities.length > 0;
  const showEmpty  = q.trim().length >= MIN_Q && !loading && !hasResults;

  // Cursor index offsets per section
  const pokemonOffset   = 0;
  const movesOffset     = results.pokemon.length;
  const abilitiesOffset = results.pokemon.length + results.moves.length;

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
        style={{ color: "#6b7199", background: "rgba(30,34,64,0.6)", border: "1px solid #1e2240" }}
        title="Recherche globale (Ctrl+K)"
      >
        <Search size={13} />
        <span className="hidden sm:inline text-xs">Rechercher…</span>
        <kbd className="hidden lg:inline text-[10px] px-1 rounded opacity-50" style={{ background: "#111428", border: "1px solid #2d3260" }}>⌃K</kbd>
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center pt-[10vh] px-4"
          style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-xl rounded-2xl overflow-hidden shadow-2xl"
            style={{ background: "#0d1020", border: "1px solid #2d3260" }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Input */}
            <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: "1px solid #1e2240" }}>
              <Search size={16} style={{ color: "#6b7199", flexShrink: 0 }} />
              <input
                ref={inputRef}
                value={q}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                placeholder="Pokémon, capacité, talent…"
                className="flex-1 bg-transparent text-[rgb(225,228,255)] placeholder:text-[#4a4f75] outline-none text-sm"
              />
              {q && (
                <button onClick={() => { setQ(""); setResults(EMPTY); inputRef.current?.focus(); }}>
                  <X size={14} style={{ color: "#6b7199" }} />
                </button>
              )}
              <kbd
                className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                style={{ background: "#111428", border: "1px solid #2d3260", color: "#4a4f75" }}
              >
                Esc
              </kbd>
            </div>

            {/* Results */}
            <div className="max-h-[60vh] overflow-y-auto py-2">
              {loading && (
                <div className="flex justify-center py-6">
                  <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}

              {!loading && showEmpty && (
                <p className="text-center text-sm py-6" style={{ color: "#4a4f75" }}>Aucun résultat pour « {q} »</p>
              )}

              {!loading && !hasResults && q.trim().length < MIN_Q && (
                <p className="text-center text-xs py-6" style={{ color: "#4a4f75" }}>Tape au moins 2 caractères…</p>
              )}

              {!loading && results.pokemon.length > 0 && (
                <Section
                  label="Pokémon"
                  Icon={BookOpen}
                  items={results.pokemon.map((p, i) => ({
                    key: p.id,
                    href: `/pokedex/${p.id}`,
                    primary: p.name_fr ?? p.name_en,
                    secondary: p.name_fr ? p.name_en : undefined,
                    badge: `#${String(p.id).padStart(3, "0")}`,
                    active: cursor === pokemonOffset + i,
                  }))}
                  onNavigate={navigate}
                />
              )}

              {!loading && results.moves.length > 0 && (
                <Section
                  label="Capacités"
                  Icon={Zap}
                  items={results.moves.map((m, i) => ({
                    key: m.id,
                    href: `/moves/${m.id}`,
                    primary: m.name_fr ?? m.name_en,
                    secondary: m.name_fr ? m.name_en : undefined,
                    badge: m.type?.name_en,
                    active: cursor === movesOffset + i,
                  }))}
                  onNavigate={navigate}
                />
              )}

              {!loading && results.abilities.length > 0 && (
                <Section
                  label="Talents"
                  Icon={Star}
                  items={results.abilities.map((a, i) => ({
                    key: a.id,
                    href: `/abilities/${a.id}`,
                    primary: a.name_fr ?? a.name_en,
                    secondary: a.name_fr ? a.name_en : undefined,
                    active: cursor === abilitiesOffset + i,
                  }))}
                  onNavigate={navigate}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

interface SectionItem {
  key: number;
  href: string;
  primary: string;
  secondary?: string;
  badge?: string;
  active: boolean;
}

function Section({
  label, Icon, items, onNavigate,
}: {
  label: string;
  Icon: React.FC<{ size?: number; className?: string }>;
  items: SectionItem[];
  onNavigate: (href: string) => void;
}) {
  return (
    <div className="mb-1">
      <div className="flex items-center gap-1.5 px-4 py-1.5">
        <Icon size={11} className="opacity-50" />
        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#4a4f75" }}>{label}</span>
      </div>
      {items.map((item) => (
        <button
          key={item.key}
          onClick={() => onNavigate(item.href)}
          className="w-full flex items-center justify-between gap-3 px-4 py-2 text-left transition-colors"
          style={{
            background: item.active ? "rgba(99,102,241,0.12)" : undefined,
            borderLeft: item.active ? "2px solid #6366f1" : "2px solid transparent",
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm truncate" style={{ color: item.active ? "#c7d2fe" : "#c8cbe8" }}>
              {item.primary}
            </span>
            {item.secondary && (
              <span className="text-xs truncate hidden sm:inline" style={{ color: "#4a4f75" }}>
                {item.secondary}
              </span>
            )}
          </div>
          {item.badge && (
            <span className="text-[10px] px-1.5 py-0.5 rounded shrink-0" style={{ background: "#111428", border: "1px solid #2d3260", color: "#6b7199" }}>
              {item.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
