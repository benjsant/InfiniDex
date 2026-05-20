"use client";

import { useState } from "react";
import { TypeBadge } from "@/components/pokemon/TypeBadge";
import { ALL_TYPES, TYPE_FR, effectiveness } from "@/lib/typeChart";

const TYPES_EN = ALL_TYPES;
const TYPES_FR = ALL_TYPES.map((t) => TYPE_FR[t]);

function multiplierBg(m: number): string {
  if (m === 0)    return "bg-gray-800 text-gray-500";
  if (m === 0.25) return "bg-green-950 text-green-200";
  if (m === 0.5)  return "bg-green-900/60 text-green-300";
  if (m === 2)    return "bg-red-900/60 text-red-300";
  if (m === 4)    return "bg-red-950 text-red-200";
  return "bg-if-card text-if-muted";
}

function multiplierText(m: number): string {
  if (m === 0)    return "0";
  if (m === 0.25) return "¼";
  if (m === 0.5)  return "½";
  if (m === 2)    return "×2";
  if (m === 4)    return "×4";
  return "×1";
}

function multiplierLabel(m: number): string {
  if (m === 0)    return "Immunité";
  if (m === 0.25) return "×¼ Très résistant";
  if (m === 0.5)  return "×½ Résistant";
  if (m === 2)    return "×2 Super efficace";
  if (m === 4)    return "×4 Très efficace";
  return "×1 Normal";
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-7 h-6 rounded flex items-center justify-center font-bold text-xs ${color}`}>×</span>
      <span className="text-if-text-xs text-xs">{label}</span>
    </div>
  );
}

// ── Desktop : tableau complet ─────────────────────────────────────────────────

function FullTable() {
  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-if-surface p-2 text-if-muted min-w-[90px]">
              ATK \ DEF
            </th>
            {TYPES_FR.map((t) => (
              <th key={t} className="p-1 min-w-[44px]">
                <TypeBadge typeName={t} size="sm" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {TYPES_EN.map((atkEn, ri) => (
            <tr key={atkEn} className="hover:bg-if-elevated">
              <td className="sticky left-0 z-10 bg-if-surface p-1">
                <TypeBadge typeName={TYPES_FR[ri]} size="sm" />
              </td>
              {TYPES_EN.map((defEn, ci) => {
                const m = effectiveness(atkEn, defEn);
                const label = m === 1 ? "" : multiplierText(m);
                return (
                  <td
                    key={defEn}
                    className={`p-1 text-center font-bold rounded-sm ${multiplierBg(m)}`}
                    style={{ width: 44, height: 32 }}
                  >
                    {label}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Mobile : sélecteur interactif ─────────────────────────────────────────────

type MobileTab = "atk" | "def";

function MobileLookup() {
  const [tab, setTab] = useState<MobileTab>("atk");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const results: { fr: string; en: string; m: number }[] = selectedIdx === null ? [] :
    TYPES_EN.map((typeEn, i) => {
      const m = tab === "atk"
        ? effectiveness(TYPES_EN[selectedIdx], typeEn)   // attacking: row = selected
        : effectiveness(typeEn, TYPES_EN[selectedIdx]);   // defending: col = selected
      return { en: typeEn, fr: TYPES_FR[i], m };
    }).filter((r) => r.m !== 1);

  const grouped: Record<string, typeof results> = {};
  for (const r of results) {
    const key = String(r.m);
    (grouped[key] = grouped[key] ?? []).push(r);
  }
  const order = [4, 2, 0.5, 0.25, 0];

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex rounded-lg overflow-hidden border border-if-border-mid text-xs font-semibold">
        <button
          onClick={() => { setTab("atk"); setSelectedIdx(null); }}
          className={`flex-1 px-3 py-2 transition-colors ${tab === "atk" ? "bg-indigo-600 text-white" : "bg-if-elevated text-if-text-xs hover:bg-if-input"}`}
        >
          Je joue ce type — contre quoi ?
        </button>
        <button
          onClick={() => { setTab("def"); setSelectedIdx(null); }}
          className={`flex-1 px-3 py-2 transition-colors ${tab === "def" ? "bg-indigo-600 text-white" : "bg-if-elevated text-if-text-xs hover:bg-if-input"}`}
        >
          Mon Pokémon est ce type — qui me frappe ?
        </button>
      </div>

      {/* Type picker */}
      <div className="grid grid-cols-3 gap-1.5">
        {TYPES_FR.map((fr, i) => (
          <button
            key={fr}
            onClick={() => setSelectedIdx(selectedIdx === i ? null : i)}
            className={`rounded-lg py-1 transition-all border text-xs font-semibold ${
              selectedIdx === i
                ? "border-indigo-500 bg-indigo-600/20"
                : "border-if-input bg-if-card hover:border-if-muted"
            }`}
          >
            <TypeBadge typeName={fr} size="sm" />
          </button>
        ))}
      </div>

      {/* Results */}
      {selectedIdx !== null && (
        <div className="space-y-3">
          <p className="text-xs text-if-text-xs">
            {tab === "atk"
              ? <>Attaquer avec <strong className="text-if-text-dim">{TYPES_FR[selectedIdx]}</strong> :</>
              : <>Défendre avec <strong className="text-if-text-dim">{TYPES_FR[selectedIdx]}</strong> contre :</>
            }
          </p>

          {order.map((m) => {
            const group = grouped[String(m)] ?? [];
            if (group.length === 0) return null;
            return (
              <div key={m} className={`rounded-lg p-3 ${multiplierBg(m)}`}>
                <p className="text-xs font-bold mb-2">{multiplierLabel(m)}</p>
                <div className="flex flex-wrap gap-1">
                  {group.map((r) => (
                    <TypeBadge key={r.en} typeName={r.fr} size="sm" />
                  ))}
                </div>
              </div>
            );
          })}

          {results.length === 0 && (
            <p className="text-xs text-center text-if-text-xs py-4">
              Aucune interaction spéciale — tout est ×1.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TypesPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2 text-if-text-hi">
        Tableau d&apos;efficacité des types
      </h1>
      <p className="text-sm text-if-text-xs mb-6">
        Génération 7 / Infinite Fusion · Lignes = attaquant · Colonnes = défenseur
      </p>

      {/* Mobile : lookup interactif */}
      <div className="block sm:hidden mb-6">
        <MobileLookup />
      </div>

      {/* Desktop : tableau complet */}
      <div className="hidden sm:block">
        <FullTable />
      </div>

      {/* Légende */}
      <div className="flex flex-wrap gap-3 mt-6">
        <LegendItem color="bg-red-950 text-red-200"    label="×4 Très efficace" />
        <LegendItem color="bg-red-900/60 text-red-300" label="×2 Super efficace" />
        <LegendItem color="bg-green-900/60 text-green-300" label="×½ Résistant" />
        <LegendItem color="bg-green-950 text-green-200"    label="×¼ Très résistant" />
        <LegendItem color="bg-gray-800 text-gray-500"  label="×0 Immunité" />
      </div>
    </div>
  );
}
