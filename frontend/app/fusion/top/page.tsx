"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { RefreshCw } from "lucide-react";
import { useFeaturedFusions } from "@/hooks/useFusion";
import { useTypes } from "@/hooks/usePokemon";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { normalize } from "@/lib/utils";

export default function FeaturedFusionsPage() {
  const { data: fusions = [], isLoading, refetch, isFetching } = useFeaturedFusions(60);
  const { data: allTypes = [] } = useTypes();
  const [typeFilter, setTypeFilter] = useState<string>("");

  const types = useMemo(
    () => allTypes.filter((t) => !t.is_triple_fusion_type),
    [allTypes],
  );

  const filtered = useMemo(() => {
    if (!typeFilter) return fusions;
    const nf = normalize(typeFilter);
    return fusions.filter(
      (f) =>
        (f.type1 && normalize(f.type1.name_en) === nf) ||
        (f.type2 && normalize(f.type2.name_en) === nf),
    );
  }, [fusions, typeFilter]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <nav aria-label="breadcrumb" className="flex items-center gap-2 text-sm text-if-text-xs mb-6">
        <Link href="/fusion" className="hover:text-[#e8b84b] transition-colors">Fusion</Link>
        <span>/</span>
        <span className="text-if-text-dim">Galerie</span>
      </nav>

      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-bold text-if-text-hi">Galerie de fusions</h1>
          <p className="text-sm text-if-muted mt-1">
            {typeFilter
              ? `Fusions de type ${typeFilter} avec sprite custom (${filtered.length})`
              : `${filtered.length} fusions avec sprite créé par la communauté`}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
            style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-text-dim)" }}
          >
            <option value="">Tous les types</option>
            {types.map((t) => (
              <option key={t.id} value={t.name_en}>
                {t.name_fr ?? t.name_en}
              </option>
            ))}
          </select>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-all"
            style={{
              background: "var(--color-if-card)",
              border: "1px solid var(--color-if-border)",
              color: "var(--color-if-muted)",
              opacity: isFetching ? 0.5 : 1,
            }}
            title="Voir d'autres fusions"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
            Autres
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-if-card border border-if-input animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-center py-12 text-sm" style={{ color: "var(--color-if-text-lo)" }}>
          Aucune fusion trouvée pour ce type.
        </p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {filtered.map((f) => (
            <Link
              key={`${f.head_id}-${f.body_id}`}
              href={`/fusion/${f.head_id}/${f.body_id}`}
              className="flex flex-col items-center gap-2 p-3 rounded-xl transition-all hover:border-indigo-500/60 group"
              style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
            >
              <Image
                src={`/api/sprites/${f.head_id}/${f.body_id}/image`}
                alt={`${f.head_name_en}/${f.body_name_en}`}
                width={80}
                height={80}
                className="rounded"
                loading="lazy"
                unoptimized
              />
              <p
                className="text-[11px] text-center font-medium leading-tight group-hover:text-indigo-300 transition-colors line-clamp-2"
                style={{ color: "var(--color-if-text-xs)" }}
              >
                {f.head_name_fr ?? f.head_name_en}/{f.body_name_fr ?? f.body_name_en}
              </p>
              <div className="flex gap-1 flex-wrap justify-center">
                {f.type1 && <TypeBadge typeName={f.type1.name_en} size="sm" />}
                {f.type2 && <TypeBadge typeName={f.type2.name_en} size="sm" />}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
