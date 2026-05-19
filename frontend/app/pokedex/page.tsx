"use client";

import { useState, useMemo, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, Star } from "lucide-react";
import Link from "next/link";
import { usePokemonList, usePokemonSearch, usePokemonCount, useTypes, useAbilities } from "@/hooks/usePokemon";
import { PokemonCard } from "@/components/pokemon/PokemonCard";
import { SearchBar } from "@/components/layout/SearchBar";
import { primaryType, secondaryType, normalize } from "@/lib/utils";
import { POKEDEX_PAGE_SIZE } from "@/lib/constants";
import type { PokemonSortBy } from "@/lib/api";

const PAGE_SIZE = POKEDEX_PAGE_SIZE;

export default function PokedexPage() {
  return (
    <Suspense>
      <PokedexContent />
    </Suspense>
  );
}

type SortBy = PokemonSortBy;

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: "id",           label: "Numéro ↑" },
  { value: "id_desc",      label: "Numéro ↓" },
  { value: "name_asc",     label: "Nom A → Z" },
  { value: "name_desc",    label: "Nom Z → A" },
  { value: "bst_desc",     label: "BST ↓" },
  { value: "bst_asc",      label: "BST ↑" },
  { value: "hp_desc",      label: "PV ↓" },
  { value: "hp_asc",       label: "PV ↑" },
  { value: "attack_desc",  label: "Attaque ↓" },
  { value: "attack_asc",   label: "Attaque ↑" },
  { value: "defense_desc", label: "Défense ↓" },
  { value: "defense_asc",  label: "Défense ↑" },
  { value: "sp_attack_desc",  label: "Atk Spé ↓" },
  { value: "sp_attack_asc",   label: "Atk Spé ↑" },
  { value: "sp_defense_desc", label: "Déf Spé ↓" },
  { value: "sp_defense_asc",  label: "Déf Spé ↑" },
  { value: "speed_desc",   label: "Vitesse ↓" },
  { value: "speed_asc",    label: "Vitesse ↑" },
];

function PokedexContent() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [typeId, setTypeId]   = useState<number | undefined>(undefined);
  const [type2Id, setType2Id] = useState<number | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [game, setGame] = useState<"kanto" | "hoenn" | "all">("kanto");
  const [sortBy, setSortBy] = useState<SortBy>("id");
  const [minBst, setMinBst] = useState<string>("");
  const [maxBst, setMaxBst] = useState<string>("");
  const [abilitySearch, setAbilitySearch] = useState<string>("");
  const [abilityId, setAbilityId] = useState<number | undefined>(undefined);

  const handleSearch = useCallback((v: string) => { setQ(v); setPage(1); }, []);
  const handleGame   = useCallback((v: "kanto" | "hoenn" | "all") => { setGame(v); setPage(1); }, []);

  const isSearching  = q.trim().length >= 2;
  const needsAllData = sortBy !== "id";

  const includeHoenn = game !== "kanto";
  const hoennOnly    = game === "hoenn";

  const parsedMinBst = minBst !== "" ? parseInt(minBst, 10) : undefined;
  const parsedMaxBst = maxBst !== "" ? parseInt(maxBst, 10) : undefined;

  const typesQuery      = useTypes();
  const abilitiesQuery  = useAbilities();
  const listQuery  = usePokemonList({
    page: needsAllData ? 1 : page,
    page_size: needsAllData ? 1000 : PAGE_SIZE,
    type_id: typeId,
    type2_id: type2Id,
    include_hoenn: includeHoenn,
    min_bst: parsedMinBst,
    max_bst: parsedMaxBst,
    sort_by: sortBy,
    ability_id: abilityId,
  });
  const countQuery  = usePokemonCount({
    type_id: typeId,
    type2_id: type2Id,
    include_hoenn: includeHoenn,
    min_bst: parsedMinBst,
    max_bst: parsedMaxBst,
    ability_id: abilityId,
  });
  const searchQuery = usePokemonSearch(q);

  const pokemons = isSearching ? searchQuery.data ?? [] : listQuery.data ?? [];
  const isLoading = isSearching ? searchQuery.isLoading : listQuery.isLoading;
  const isError   = isSearching ? searchQuery.isError   : listQuery.isError;

  const types = useMemo(
    () => (typesQuery.data ?? []).filter((t) => !t.is_triple_fusion_type),
    [typesQuery.data],
  );

  // Quand on cherche, on garde l'intersection recherche × filtres × tri côté client.
  const filtered = useMemo(() => {
    let result = pokemons;
    if (isSearching && hoennOnly)        result = result.filter((p) => p.is_hoenn_only);
    if (isSearching && game === "kanto") result = result.filter((p) => !p.is_hoenn_only);
    if (isSearching && typeId) {
      const target = types.find((t) => t.id === typeId);
      if (target) {
        const nf = normalize(target.name_en);
        result = result.filter((p) => {
          const t1 = primaryType(p.types);
          const t2 = secondaryType(p.types);
          return (t1 && normalize(t1.name_en) === nf) || (t2 && normalize(t2.name_en) === nf);
        });
      }
    }
    if (isSearching && type2Id) {
      const target2 = types.find((t) => t.id === type2Id);
      if (target2) {
        const nf2 = normalize(target2.name_en);
        result = result.filter((p) => {
          const t1 = primaryType(p.types);
          const t2 = secondaryType(p.types);
          return (t1 && normalize(t1.name_en) === nf2) || (t2 && normalize(t2.name_en) === nf2);
        });
      }
    }
    if (isSearching && parsedMinBst !== undefined) result = result.filter((p) => p.bst >= parsedMinBst);
    if (isSearching && parsedMaxBst !== undefined) result = result.filter((p) => p.bst <= parsedMaxBst);
    if (isSearching && needsAllData) {
      result = [...result].sort((a, b) => {
        if (sortBy === "id_desc")   return b.id - a.id;
        if (sortBy === "bst_desc")  return b.bst - a.bst;
        if (sortBy === "bst_asc")   return a.bst - b.bst;
        if (sortBy === "name_asc")  return (a.name_fr ?? a.name_en).localeCompare(b.name_fr ?? b.name_en, "fr");
        if (sortBy === "name_desc") return (b.name_fr ?? b.name_en).localeCompare(a.name_fr ?? a.name_en, "fr");
        // stat sorts
        const stat = sortBy.replace(/_asc$|_desc$/, "") as keyof typeof a;
        const dir = sortBy.endsWith("_desc") ? -1 : 1;
        return dir * (((a[stat] as number) ?? 0) - ((b[stat] as number) ?? 0));
      });
    }
    return result;
  }, [pokemons, typeId, type2Id, types, isSearching, hoennOnly, game, parsedMinBst, parsedMaxBst, needsAllData, sortBy]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-if-text-hi">Pokédex</h1>
          <Link
            href="/pokedex/favorites"
            className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg transition-all"
            style={{ background: "rgba(232,184,75,0.1)", border: "1px solid rgba(232,184,75,0.25)", color: "#e8b84b" }}
          >
            <Star size={11} />
            Favoris
          </Link>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-if-border-mid text-xs font-semibold">
          {(["kanto", "hoenn", "all"] as const).map((v) => (
            <button
              key={v}
              onClick={() => handleGame(v)}
              className={`px-3 py-1.5 transition-colors ${game === v ? "bg-indigo-600 text-white" : "bg-if-elevated text-if-text-xs hover:bg-if-input"}`}
            >
              {v === "kanto" ? "IF Kanto (501)" : v === "hoenn" ? "IF Hoenn (71)" : "Tous (572)"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <SearchBar
            onSearch={handleSearch}
            className="flex-1"
            placeholder="Rechercher (Bulbasaur, Bulbizarre, pikachu…)"
          />
          <select
            value={typeId ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setTypeId(v ? Number(v) : undefined);
              setPage(1);
            }}
            className="px-3 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi focus:outline-none focus:border-indigo-500"
          >
            <option value="">1er type</option>
            {types.map((t) => (
              <option key={t.id} value={t.id}>{t.name_fr} ({t.name_en})</option>
            ))}
          </select>
          <select
            value={type2Id ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setType2Id(v ? Number(v) : undefined);
              setPage(1);
            }}
            className="px-3 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi focus:outline-none focus:border-indigo-500"
          >
            <option value="">+ 2ᵉ type</option>
            {types.map((t) => (
              <option key={t.id} value={t.id}>{t.name_fr} ({t.name_en})</option>
            ))}
          </select>
        </div>

        {/* Ability + BST row */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <datalist id="ability-list">
              {(abilitiesQuery.data ?? []).map((a) => (
                <option key={a.id} value={a.name_fr ?? a.name_en} />
              ))}
            </datalist>
            <input
              type="text"
              list="ability-list"
              placeholder="Talent…"
              value={abilitySearch}
              onChange={(e) => {
                const val = e.target.value;
                setAbilitySearch(val);
                const match = (abilitiesQuery.data ?? []).find(
                  (a) => (a.name_fr ?? a.name_en).toLowerCase() === val.toLowerCase()
                );
                setAbilityId(match?.id);
                setPage(1);
              }}
              className="w-36 px-3 py-1.5 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi text-sm focus:outline-none focus:border-indigo-500"
            />
            {abilitySearch && (
              <button
                onClick={() => { setAbilitySearch(""); setAbilityId(undefined); setPage(1); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-if-muted hover:text-white"
                aria-label="Effacer le talent"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Sort + BST row */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value as SortBy); setPage(1); }}
            className="px-3 py-1.5 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi text-sm focus:outline-none focus:border-indigo-500"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <div className="flex items-center gap-2 text-sm text-if-text-xs">
            <span>BST</span>
            <input
              type="number"
              min={0}
              max={1000}
              placeholder="min"
              value={minBst}
              onChange={(e) => { setMinBst(e.target.value); setPage(1); }}
              className="w-20 px-2 py-1.5 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi text-sm focus:outline-none focus:border-indigo-500"
            />
            <span>—</span>
            <input
              type="number"
              min={0}
              max={1000}
              placeholder="max"
              value={maxBst}
              onChange={(e) => { setMaxBst(e.target.value); setPage(1); }}
              className="w-20 px-2 py-1.5 rounded-lg bg-if-input border border-if-border-mid text-if-text-hi text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <SkeletonGrid />
      ) : isError ? (
        <p className="text-center text-if-text-xs py-12">Impossible de charger les Pokémon.</p>
      ) : filtered.length === 0 ? (
        <p className="text-center text-if-text-xs py-12">Aucun Pokémon trouvé.</p>
      ) : (
        <>
          <p className="text-sm text-if-text-xs mb-4">
            {isSearching
              ? `${filtered.length} Pokémon pour "${q}"`
              : needsAllData
              ? `${filtered.length} Pokémon`
              : `${countQuery.data ?? "…"} Pokémon`}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {filtered.map((p) => <PokemonCard key={p.id} pokemon={p} />)}
          </div>

          {!isSearching && !needsAllData && (
            <div className="flex justify-center gap-3 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-lo disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
              >
                <ChevronLeft size={16} className="inline" /> Précédent
              </button>
              <span className="px-4 py-2 text-if-text-xs">
                Page {page}
                {countQuery.data !== undefined && (
                  <span> / {Math.ceil(countQuery.data / PAGE_SIZE)}</span>
                )}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={
                  pokemons.length < PAGE_SIZE ||
                  (countQuery.data !== undefined && page >= Math.ceil(countQuery.data / PAGE_SIZE))
                }
                className="px-4 py-2 rounded-lg bg-if-input border border-if-border-mid text-if-text-lo disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
              >
                Suivant <ChevronRight size={16} className="inline" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      {Array.from({ length: 40 }).map((_, i) => (
        <div key={i} className="h-40 rounded-xl bg-if-elevated border border-if-input animate-pulse" />
      ))}
    </div>
  );
}
