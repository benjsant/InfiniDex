"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, MapPin, Package, ShoppingBag, Star } from "lucide-react";
import { useItems, useItemSearch } from "@/hooks/useItems";
import { SearchBar } from "@/components/layout/SearchBar";
import { normalize } from "@/lib/utils";
import type { ItemLocationOut, ItemOut } from "@/types/api";

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

const METHOD_LABELS: Record<ItemLocationOut["method"], string> = {
  shop:  "Boutiques",
  found: "Trouvé / Donné",
  wild:  "Pokémon sauvages",
  other: "Autre",
};

const METHOD_ICONS: Record<ItemLocationOut["method"], React.ReactNode> = {
  shop:  <ShoppingBag size={11} />,
  found: <Star size={11} />,
  wild:  <MapPin size={11} />,
  other: <MapPin size={11} />,
};

function LocationsPanel({ locations }: { locations: ItemLocationOut[] }) {
  if (!locations.length) return (
    <p className="text-xs italic" style={{ color: "var(--color-if-text-lo)" }}>Aucune localisation connue.</p>
  );

  const byMethod = locations.reduce<Record<string, ItemLocationOut[]>>((acc, loc) => {
    (acc[loc.method] ??= []).push(loc);
    return acc;
  }, {});

  const order: ItemLocationOut["method"][] = ["shop", "found", "wild", "other"];

  return (
    <div className="flex flex-wrap gap-4">
      {order.map((method) => {
        const locs = byMethod[method];
        if (!locs?.length) return null;
        return (
          <div key={method}>
            <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-if-muted)" }}>
              {METHOD_ICONS[method]}
              {METHOD_LABELS[method]}
            </p>
            <ul className="space-y-0.5">
              {locs.map((loc) => (
                <li key={loc.id} className="text-xs" style={{ color: "var(--color-if-text-dim)" }}>
                  {loc.location_name}
                  {loc.notes && (
                    <span className="ml-1" style={{ color: "var(--color-if-muted)" }}>({loc.notes})</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

function ItemRow({ item }: { item: ItemOut }) {
  const [open, setOpen] = useState(false);
  const hasLocations = item.locations.length > 0;
  const colSpan = 5;

  return (
    <>
      <tr
        className="border-t transition-colors hover:bg-if-border cursor-pointer select-none"
        style={{ borderColor: "var(--color-if-border-lo)" }}
        onClick={() => setOpen((o) => !o)}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-1.5">
            {open
              ? <ChevronDown size={13} style={{ color: "var(--color-if-muted)", flexShrink: 0 }} />
              : <ChevronRight size={13} style={{ color: "var(--color-if-muted)", flexShrink: 0 }} />
            }
            <span className="font-medium" style={{ color: "var(--color-if-text)" }}>
              {item.name_fr ?? item.name_en}
            </span>
            {item.name_fr && (
              <span className="ml-0.5 text-xs hidden sm:inline" style={{ color: "var(--color-if-muted)" }}>
                ({item.name_en})
              </span>
            )}
          </div>
        </td>
        <td className="px-3 py-2.5">
          <CategoryBadge category={item.category} />
        </td>
        <td className="hidden md:table-cell px-3 py-2.5 text-sm max-w-xs" style={{ color: "var(--color-if-text-xs)" }}>
          {item.effect ?? "—"}
        </td>
        <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums" style={{ color: "var(--color-if-text-dim)" }}>
          {formatPrice(item.price_buy)}
        </td>
        <td className="hidden sm:table-cell px-3 py-2.5 text-right font-mono text-xs tabular-nums" style={{ color: "var(--color-if-muted)" }}>
          {formatPrice(item.price_sell)}
        </td>
      </tr>
      {open && (
        <tr style={{ borderColor: "var(--color-if-border-lo)", background: "var(--color-if-bg)" }}>
          <td colSpan={colSpan} className="px-6 py-3 border-t" style={{ borderColor: "var(--color-if-border-lo)" }}>
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-if-text-lo)" }}>
              Localisations
            </p>
            <LocationsPanel locations={item.locations} />
          </td>
        </tr>
      )}
    </>
  );
}

export default function ItemsPage() {
  const [q, setQ]               = useState("");
  const [catFilter, setCatFilter] = useState<Category | "">("");

  const searching = q.trim().length >= 2;
  const { data: allItems = [],    isLoading: loadingAll,    isError: errorAll    } = useItems(catFilter || undefined);
  const { data: searchResults = [], isLoading: loadingSearch, isError: errorSearch } = useItemSearch(searching ? q : "");

  const isLoading = searching ? loadingSearch : loadingAll;
  const isError   = searching ? errorSearch   : errorAll;

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
        <h1 className="text-2xl font-bold" style={{ color: "var(--color-if-text)" }}>Objets</h1>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <SearchBar onSearch={setQ} placeholder="Rechercher un objet…" className="flex-1" />
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value as Category | "")}
          className="px-3 py-2 rounded-lg focus:outline-none"
          style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-text)" }}
        >
          <option value="">Toutes catégories</option>
          {categoryOrder.map((c) => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
      </div>

      <p className="text-sm mb-4" style={{ color: "var(--color-if-muted)" }}>
        {items.length} objet{items.length !== 1 ? "s" : ""}
      </p>

      {isLoading ? (
        <div className="animate-pulse space-y-2">
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className="h-10 rounded" style={{ background: "var(--color-if-card)" }} />
          ))}
        </div>
      ) : isError ? (
        <p className="text-center py-16 text-sm" style={{ color: "var(--color-if-muted)" }}>Impossible de charger les objets.</p>
      ) : items.length === 0 ? (
        <p className="text-center py-16" style={{ color: "var(--color-if-muted)" }}>Aucun objet trouvé.</p>
      ) : catFilter || searching ? (
        <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid var(--color-if-border)" }}>
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
                  <span className="text-xs" style={{ color: "var(--color-if-muted)" }}>— {rows.length} objet{rows.length !== 1 ? "s" : ""}</span>
                </div>
                <div className="overflow-x-auto rounded-lg" style={{ border: "1px solid var(--color-if-border)" }}>
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
      <tr className="text-xs" style={{ background: "var(--color-if-surface)", color: "var(--color-if-muted)" }}>
        <th className="px-3 py-2 text-left">Objet</th>
        <th className="px-3 py-2 text-left">Catégorie</th>
        <th className="hidden md:table-cell px-3 py-2 text-left">Effet</th>
        <th className="px-3 py-2 text-right">Achat</th>
        <th className="hidden sm:table-cell px-3 py-2 text-right">Vente</th>
      </tr>
    </thead>
  );
}
