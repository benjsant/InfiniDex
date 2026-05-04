"use client";

import { useQuery } from "@tanstack/react-query";
import { getTypes } from "@/lib/api";
import { TypeBadge } from "@/components/pokemon/TypeBadge";

// Gen 7 type effectiveness chart (rows = attacking, cols = defending)
// Value: 0 = immune, 0.5 = resistant, 2 = super effective, 1 = normal
// Source: same data as backend seed_type_effectiveness.py
const TYPES_EN = [
  "Normal","Fire","Water","Electric","Grass","Ice",
  "Fighting","Poison","Ground","Flying","Psychic","Bug",
  "Rock","Ghost","Dragon","Dark","Steel","Fairy",
];
const TYPES_FR = [
  "Normal","Feu","Eau","Électrik","Plante","Glace",
  "Combat","Poison","Sol","Vol","Psy","Insecte",
  "Roche","Spectre","Dragon","Ténèbres","Acier","Fée",
];

// Row = attacking type, Col = defending type
// 0=immune, 0.5=resist, 2=super, 1=normal
const CHART: Record<string, Record<string, number>> = {
  Normal:   { Rock: 0.5, Ghost: 0, Steel: 0.5 },
  Fire:     { Fire: 0.5, Water: 0.5, Grass: 2, Ice: 2, Bug: 2, Rock: 0.5, Dragon: 0.5, Steel: 2 },
  Water:    { Fire: 2, Water: 0.5, Grass: 0.5, Ground: 2, Rock: 2, Dragon: 0.5 },
  Electric: { Water: 2, Electric: 0.5, Grass: 0.5, Ground: 0, Flying: 2, Dragon: 0.5 },
  Grass:    { Fire: 0.5, Water: 2, Grass: 0.5, Poison: 0.5, Ground: 2, Flying: 0.5, Bug: 0.5, Rock: 2, Dragon: 0.5, Steel: 0.5 },
  Ice:      { Water: 0.5, Grass: 2, Ice: 0.5, Ground: 2, Flying: 2, Dragon: 2, Steel: 0.5 },
  Fighting: { Normal: 2, Ice: 2, Poison: 0.5, Flying: 0.5, Psychic: 0.5, Bug: 0.5, Rock: 2, Ghost: 0, Dark: 2, Steel: 2, Fairy: 0.5 },
  Poison:   { Grass: 2, Poison: 0.5, Ground: 0.5, Rock: 0.5, Ghost: 0.5, Steel: 0, Fairy: 2 },
  Ground:   { Fire: 2, Electric: 2, Grass: 0.5, Poison: 2, Flying: 0, Bug: 0.5, Rock: 2, Steel: 2 },
  Flying:   { Electric: 0.5, Grass: 2, Fighting: 2, Bug: 2, Rock: 0.5, Steel: 0.5 },
  Psychic:  { Fighting: 2, Poison: 2, Psychic: 0.5, Dark: 0, Steel: 0.5 },
  Bug:      { Fire: 0.5, Grass: 2, Fighting: 0.5, Flying: 0.5, Ghost: 0.5, Steel: 0.5, Fairy: 0.5 },
  Rock:     { Fire: 2, Ice: 2, Fighting: 0.5, Ground: 0.5, Flying: 2, Bug: 2, Steel: 0.5 },
  Ghost:    { Normal: 0, Psychic: 2, Ghost: 2, Dark: 0.5 },
  Dragon:   { Dragon: 2, Steel: 0.5, Fairy: 0 },
  Dark:     { Fighting: 0.5, Psychic: 2, Ghost: 2, Dark: 0.5, Fairy: 0.5 },
  Steel:    { Fire: 0.5, Water: 0.5, Electric: 0.5, Ice: 2, Rock: 2, Steel: 0.5, Fairy: 2 },
  Fairy:    { Fire: 0.5, Fighting: 2, Poison: 0.5, Dragon: 2, Dark: 2, Steel: 0.5 },
};

function getMultiplier(atk: string, def: string): number {
  return CHART[atk]?.[def] ?? 1;
}

function multiplierBg(m: number): string {
  if (m === 0)   return "bg-gray-800 text-gray-500";
  if (m === 0.5) return "bg-green-900/60 text-green-300";
  if (m === 0.25) return "bg-green-950 text-green-200";
  if (m === 2)   return "bg-red-900/60 text-red-300";
  if (m === 4)   return "bg-red-950 text-red-200";
  return "bg-if-deep text-if-muted";
}

function multiplierText(m: number): string {
  if (m === 0)   return "0";
  if (m === 0.25) return "¼";
  if (m === 0.5) return "½";
  if (m === 2)   return "2";
  if (m === 4)   return "4";
  return "";
}

export default function TypesPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2 text-if-text-hi">
        Tableau d&apos;efficacité des types
      </h1>
      <p className="text-sm text-if-text-xs mb-6">
        Génération 7 / Infinite Fusion · Lignes = attaquant · Colonnes = défenseur
      </p>

      <div className="overflow-x-auto">
        <table className="text-xs border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-if-deep p-2 text-if-muted min-w-[90px]">
                ATK \ DEF
              </th>
              {TYPES_FR.map((t, i) => (
                <th key={t} className="p-1 min-w-[44px]">
                  <TypeBadge typeName={t} size="sm" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TYPES_EN.map((atkEn, ri) => {
              const atkFr = TYPES_FR[ri];
              return (
                <tr key={atkEn} className="hover:bg-if-surface">
                  <td className="sticky left-0 z-10 bg-if-deep p-1">
                    <TypeBadge typeName={atkFr} size="sm" />
                  </td>
                  {TYPES_EN.map((defEn, ci) => {
                    const m = getMultiplier(atkEn, defEn);
                    const label = multiplierText(m);
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
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-6 text-xs">
        <LegendItem color="bg-red-900/60 text-red-300" label="×2 Super efficace" />
        <LegendItem color="bg-green-900/60 text-green-300" label="×½ Pas très efficace" />
        <LegendItem color="bg-gray-800 text-gray-500" label="×0 Immunité" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-5 h-5 rounded flex items-center justify-center font-bold ${color}`}>
        ×
      </span>
      <span className="text-if-text-xs">{label}</span>
    </div>
  );
}
