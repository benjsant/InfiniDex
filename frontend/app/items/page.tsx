"use client";

import { useState, useMemo } from "react";
import { Package } from "lucide-react";
import { useItems, useItemSearch } from "@/hooks/useItems";
import { SearchBar } from "@/components/layout/SearchBar";
import { normalize } from "@/lib/utils";
import type { ItemOut } from "@/types/api";

type Category = "fusion" | "evolution" | "valuable";

const CATEGORY_LABELS: Record<Category, string> = {
  fusion:    "Fusion",
  evolution: "Évolution",
  valuable:  "Précieux",
};

const CATEGORY_COLORS: Record<Category, string> = {
  fusion:    "#7c6fe0",
  evolution: "#4ea87a",
  valuable:  "#d4a017",
};

function formatPrice(p: number | null) {
  if (p === null) return "—";
  return `₽${p.toLocaleString("fr-FR")}`;
}

function CategoryBadge({ category }: { category: Category }) {
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-medium"
      style={{ background: `${CATEGORY_COLORS[category]}22`, color: CATEGORY_COLORS[category] }}
    >
      {CATEGORY_LABELS[category]}
    </span>
  );
}

function ItemRow({ item }: { item: ItemOut }) {
  return (
    <tr
      className="border-t transition-colors hover:bg-[#1e2240]"
      style={{ borderColor: "#1a1d35" }}
    >
      <td className="px-3 py-2.5">
        <span className="font-medium" style={{ color: "#e1e4ff" }}>
          {item.name_fr ?? item.name_en}
        </span>
        {item.name_fr && (
          <span className="ml-1.5 text-xs hidden sm:inline" style={{ color: "#6b7199" }}>
            ({item.name_en})
          </span>
        )}
      </td>
      <td className="px-3 py-2.5">
        <CategoryBadge category={item.category} />
      </td>
      <td className="hidden md:table-cell px-3 py-2.5 text-sm max-w-xs" style={{ color: "#9aa0c0" }}>
        {item.effect ?? "—"}
      </td>
      <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums" style={{ color: "#c8cbf0" }}>
        {formatPrice(item.price_buy)}
      </td>
      <td className="hidden sm:table-cell px-3 py-2.5 text-right font-mono text-xs tabular-nums" style={{ color: "#6b7199" }}>
        {formatPrice(item.price_sell)}
      </td>
    </tr>
  );
}

export default function ItemsPage() {
  const [q, setQ]               = useState("");
  const [catFilter, setCatFilter] = useState<Category | "">("");

  const searching = q.trim().length >= 2;
  const { data: allItems = [],    isLoading: loadingAll  } = useItems(catFilter || undefined);
  const { data: searchResults = [], isLoading: loadingSearch } = useItemSearch(searching ? q : "");

  const isLoading = searching ? loadingSearch : loadingAll;

  const items = useMemo<ItemOut[]>(() => {
    if (searching) {
      const filtered = catFilter
        ? searchResults.filter((i) => i.category === catFilter)
        : searchResults;
      return filtered;
    }
    if (q.trim().length < 2 && q.trim().length > 0) {
      const nq = normalize(q);
      return allItems.filter(
        (i) =>
          normalize(i.name_en).includes(nq) ||
          (i.name_fr && normalize(i.name_fr).includes(nq)),
      );
    }
    return allItems;
  }, [searching, searchResults, allItems, catFilter, q]);

  const byCategory = useMemo(() => {
    const groups: Record<string, ItemOut[]> = {};
    for (const item of items) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return groups;
  }, [items]);

  const categoryOrder: Category[] = ["fusion", "evolution", "valuable"];

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <Package size={22} className="text-indigo-400" />
        <h1 className="text-2xl font-bold" style={{ color: "#e1e4ff" }}>Objets</h1>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <SearchBar onSearch={setQ} placeholder="Rechercher un objet…" className="flex-1" />
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value as Category | "")}
          className="px-3 py-2 rounded-lg focus:outline-none"
          style={{ background: "#111428", border: "1px solid #1e2240", color: "#e1e4ff" }}
        >
          <option value="">Toutes catégories</option>
          {categoryOrder.map((c) => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
      </div>

      <p className="text-sm mb-4" style={{ color: "#6b7199" }}>
        {items.length} objet{items.length !== 1 ? "s" : ""}
      </p>

      {isLoading ? (
        <div className="animate-pulse space-y-2">
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className="h-10 rounded" style={{ background: "#191925" }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-center py-16" style={{ color: "#6b7199" }}>Aucun objet trouvé.</p>
      ) : catFilter || searching ? (
        <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid #1e2240" }}>
          <table className="w-full text-sm" style={{ minWidth: "360px" }}>
            <TableHead />
            <tbody>
              {items.map((item) => <ItemRow key={item.id} item={item} />)}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="space-y-8">
          {categoryOrder.map((cat) => {
            const rows = byCategory[cat];
            if (!rows?.length) return null;
            return (
              <section key={cat}>
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className="text-sm font-semibold"
                    style={{ color: CATEGORY_COLORS[cat] }}
                  >
                    {CATEGORY_LABELS[cat]}
                  </span>
                  <span className="text-xs" style={{ color: "#6b7199" }}>— {rows.length} objet{rows.length !== 1 ? "s" : ""}</span>
                </div>
                <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid #1e2240" }}>
                  <table className="w-full text-sm" style={{ minWidth: "360px" }}>
                    <TableHead />
                    <tbody>
                      {rows.map((item) => <ItemRow key={item.id} item={item} />)}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TableHead() {
  return (
    <thead>
      <tr className="text-xs" style={{ background: "#0f1225", color: "#6b7199" }}>
        <th className="px-3 py-2 text-left">Objet</th>
        <th className="px-3 py-2 text-left">Catégorie</th>
        <th className="hidden md:table-cell px-3 py-2 text-left">Effet</th>
        <th className="px-3 py-2 text-right">Achat</th>
        <th className="hidden sm:table-cell px-3 py-2 text-right">Vente</th>
      </tr>
    </thead>
  );
}
