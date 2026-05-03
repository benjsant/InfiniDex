"use client";

import { useState, useMemo, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { usePokemonList, usePokemonSearch, useTypes } from "@/hooks/usePokemon";
import { PokemonCard } from "@/components/pokemon/PokemonCard";
import { SearchBar } from "@/components/layout/SearchBar";
import { primaryType, secondaryType, normalize } from "@/lib/utils";
import { POKEDEX_PAGE_SIZE } from "@/lib/constants";

const PAGE_SIZE = POKEDEX_PAGE_SIZE;

export default function PokedexPage() {
  return (
    <Suspense>
      <PokedexContent />
    </Suspense>
  );
}

function PokedexContent() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [typeId, setTypeId] = useState<number | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [game, setGame] = useState<"kanto" | "hoenn" | "all">("kanto");
  const [legendaryOnly, setLegendaryOnly] = useState(false);

  const handleSearch = useCallback((v: string) => { setQ(v); setPage(1); }, []);
  const handleGame   = useCallback((v: "kanto" | "hoenn" | "all") => { setGame(v); setPage(1); }, []);

  const isSearching = q.trim().length >= 2;

  const includeHoenn = game !== "kanto";
  const hoennOnly    = game === "hoenn";

  const typesQuery  = useTypes();
  const listQuery   = usePokemonList({ page, page_size: PAGE_SIZE, type_id: typeId, include_hoenn: includeHoenn, legendary: legendaryOnly || undefined });
  const searchQuery = usePokemonSearch(q);

  const pokemons = isSearching ? searchQuery.data ?? [] : listQuery.data ?? [];
  const isLoading = isSearching ? searchQuery.isLoading : listQuery.isLoading;

  const types = useMemo(
    () => (typesQuery.data ?? []).filter((t) => !t.is_triple_fusion_type),
    [typesQuery.data],
  );

  // Quand on cherche, on garde l'intersection recherche × type × game côté client
  // (l'endpoint /search ne prend pas de type_id ni include_hoenn).
  const filtered = useMemo(() => {
    let result = pokemons;
    if (isSearching && hoennOnly)        result = result.filter((p) => p.is_hoenn_only);
    if (isSearching && game === "kanto") result = result.filter((p) => !p.is_hoenn_only);
    if (legendaryOnly)                   result = result.filter((p) => p.is_legendary);
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
    return result;
  }, [pokemons, typeId, types, isSearching, hoennOnly, game]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-[rgb(220,220,255)]">Pokédex</h1>
        <div className="flex rounded-lg overflow-hidden border border-[rgb(50,50,70)] text-xs font-semibold">
          {(["kanto", "hoenn", "all"] as const).map((v) => (
            <button
              key={v}
              onClick={() => handleGame(v)}
              className={`px-3 py-1.5 transition-colors ${game === v ? "bg-indigo-600 text-white" : "bg-[rgb(25,25,38)] text-[rgb(140,140,170)] hover:bg-[rgb(35,35,50)]"}`}
            >
              {v === "kanto" ? "IF Kanto (501)" : v === "hoenn" ? "IF Hoenn (71)" : "Tous (572)"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
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
          className="px-3 py-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(220,220,255)] focus:outline-none focus:border-indigo-500"
        >
          <option value="">Tous les types</option>
          {types.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name_fr} ({t.name_en})
            </option>
          ))}
        </select>
        <button
          onClick={() => { setLegendaryOnly((v) => !v); setPage(1); }}
          className={`px-3 py-2 rounded-lg border text-sm font-semibold transition-colors ${legendaryOnly ? "bg-yellow-500/20 border-yellow-500 text-yellow-300" : "bg-[rgb(30,30,42)] border-[rgb(50,50,70)] text-[rgb(140,140,170)] hover:border-yellow-500 hover:text-yellow-300"}`}
        >
          ★ Légendaires
        </button>
      </div>

      {isLoading ? (
        <SkeletonGrid />
      ) : filtered.length === 0 ? (
        <p className="text-center text-[rgb(120,120,140)] py-12">Aucun Pokémon trouvé.</p>
      ) : (
        <>
          <p className="text-sm text-[rgb(120,120,140)] mb-4">
            {filtered.length} Pokémon{isSearching ? ` pour "${q}"` : ""}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {filtered.map((p) => <PokemonCard key={p.id} pokemon={p} />)}
          </div>

          {!isSearching && (
            <div className="flex justify-center gap-3 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
              >
                <ChevronLeft size={16} className="inline" /> Précédent
              </button>
              <span className="px-4 py-2 text-[rgb(120,120,140)]">Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={pokemons.length < PAGE_SIZE}
                className="px-4 py-2 rounded-lg bg-[rgb(30,30,42)] border border-[rgb(50,50,70)] text-[rgb(160,160,180)] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition-all"
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
        <div key={i} className="h-40 rounded-xl bg-[rgb(25,25,35)] border border-[rgb(40,40,55)] animate-pulse" />
      ))}
    </div>
  );
}
