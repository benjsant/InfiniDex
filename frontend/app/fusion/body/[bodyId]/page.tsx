"use client";

import { use, useState, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePokemon, usePokemonList, useTypes } from "@/hooks/usePokemon";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { normalize, primaryType, secondaryType } from "@/lib/utils";
import type { PokemonListItem } from "@/types/api";

const PAGE_SIZE = 40;

type SortMode = "bst_desc" | "bst_asc" | "id";

export default function FusionsByBodyPage({ params }: { params: Promise<{ bodyId: string }> }) {
  const { bodyId } = use(params);
  const bId = parseInt(bodyId, 10);

  const { data: body, isLoading: bodyLoading } = usePokemon(bId);
  const { data: heads = [], isLoading: headsLoading } = usePokemonList({
    page_size: 600,
    include_hoenn: true,
  });
  const { data: allTypes = [] } = useTypes();

  const [typeFilter, setTypeFilter] = useState<string>("");
  const [sortMode, setSortMode] = useState<SortMode>("bst_desc");
  const [page, setPage] = useState(1);

  const types = useMemo(() => allTypes.filter((t) => !t.is_triple_fusion_type), [allTypes]);

  const filtered = useMemo(() => {
    let list: PokemonListItem[] = heads.filter((h) => h.id !== bId);

    if (typeFilter) {
      const nf = normalize(typeFilter);
      list = list.filter((h) => {
        const t1 = primaryType(h.types);
        const t2 = secondaryType(h.types);
        return (t1 && normalize(t1.name_en) === nf) || (t2 && normalize(t2.name_en) === nf);
      });
    }

    list = [...list].sort((a, b) => {
      if (sortMode === "bst_desc") return b.bst - a.bst;
      if (sortMode === "bst_asc")  return a.bst - b.bst;
      return a.id - b.id;
    });

    return list;
  }, [heads, bId, typeFilter, sortMode]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const bodyName = body ? (body.name_fr ?? body.name_en) : `#${bId}`;

  if (bodyLoading) return (
    <div className="max-w-4xl mx-auto px-4 py-8 animate-pulse space-y-4">
      <div className="h-8 w-64 rounded bg-if-border" />
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {Array.from({ length: 20 }).map((_, i) => <div key={i} className="h-36 rounded-xl bg-if-border" />)}
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <nav aria-label="breadcrumb" className="flex items-center gap-2 text-sm text-if-text-xs mb-4">
        <Link href="/fusion" className="hover:text-[#e8b84b] transition-colors">Fusion</Link>
        <span>/</span>
        <Link href={`/pokedex/${bId}`} className="hover:text-[#e8b84b] transition-colors">{bodyName}</Link>
        <span>/</span>
        <span className="text-if-text-dim">en corps</span>
      </nav>

      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
        <div className="flex items-center gap-3">
          {body && (
            <Image
              src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${body.national_id ?? bId}.png`}
              alt={bodyName}
              width={56}
              height={56}
              unoptimized
              className="object-contain"
            />
          )}
          <div>
            <h1 className="text-xl font-bold text-if-text-hi">{bodyName} en corps</h1>
            <p className="text-sm text-if-muted">
              {filtered.length} fusions possibles
            </p>
          </div>
        </div>

        <div className="flex gap-2 ml-auto flex-wrap">
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="px-3 py-1.5 rounded-lg text-sm focus:outline-none"
            style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-text-dim)" }}
          >
            <option value="">Tous les types</option>
            {types.map((t) => (
              <option key={t.id} value={t.name_en}>{t.name_fr ?? t.name_en}</option>
            ))}
          </select>
          <select
            value={sortMode}
            onChange={(e) => { setSortMode(e.target.value as SortMode); setPage(1); }}
            className="px-3 py-1.5 rounded-lg text-sm focus:outline-none"
            style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-text-dim)" }}
          >
            <option value="bst_desc">BST tête ↓</option>
            <option value="bst_asc">BST tête ↑</option>
            <option value="id">N° ↑</option>
          </select>
        </div>
      </div>

      {headsLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3 animate-pulse">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => <div key={i} className="h-36 rounded-xl bg-if-border" />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3">
            {paginated.map((head) => {
              const t1 = primaryType(head.types);
              const t2 = secondaryType(head.types);
              return (
                <Link
                  key={head.id}
                  href={`/fusion/${head.id}/${bId}`}
                  className="group flex flex-col items-center gap-1.5 p-3 rounded-xl transition-all"
                  style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#6366f166"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--color-if-border)"; }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/api/sprites/${head.id}/${bId}/image`}
                    alt={`${head.name_fr ?? head.name_en}/${bodyName}`}
                    width={64}
                    height={64}
                    loading="lazy"
                    style={{ imageRendering: "pixelated", objectFit: "contain" }}
                    className="group-hover:scale-110 transition-transform duration-150"
                    onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0.3"; }}
                  />
                  <p className="text-xs font-medium text-center text-if-text-dim leading-tight truncate w-full text-center group-hover:text-[#e8b84b] transition-colors">
                    {head.name_fr ?? head.name_en}
                  </p>
                  <div className="flex gap-1 flex-wrap justify-center">
                    {t1 && <TypeBadge typeName={t1.name_en} label={t1.name_fr ?? t1.name_en} size="sm" />}
                    {t2 && <TypeBadge typeName={t2.name_en} label={t2.name_fr ?? t2.name_en} size="sm" />}
                  </div>
                  <p className="text-[10px] font-mono" style={{ color: "var(--color-if-text-lo)" }}>
                    BST {head.bst}
                  </p>
                </Link>
              );
            })}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg text-sm disabled:opacity-30 transition-all"
                style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-muted)" }}
              >
                ← Précédent
              </button>
              <span className="text-sm" style={{ color: "var(--color-if-text-lo)" }}>
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 rounded-lg text-sm disabled:opacity-30 transition-all"
                style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-muted)" }}
              >
                Suivant →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
