/**
 * Gen 6+ type effectiveness chart.
 * offensiveChart[attackingType][defendingType] = multiplier
 * Only non-1× entries are stored; missing = 1.
 */
export const offensiveChart: Record<string, Record<string, number>> = {
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
  Bug:      { Fire: 0.5, Grass: 2, Fighting: 0.5, Poison: 0.5, Flying: 0.5, Psychic: 2, Ghost: 0.5, Dark: 2, Steel: 0.5, Fairy: 0.5 },
  Rock:     { Fire: 2, Ice: 2, Fighting: 0.5, Ground: 0.5, Flying: 2, Bug: 2, Steel: 0.5 },
  Ghost:    { Normal: 0, Fighting: 0, Psychic: 2, Ghost: 2, Dark: 0.5 },
  Dragon:   { Dragon: 2, Steel: 0.5, Fairy: 0 },
  Dark:     { Fighting: 0.5, Psychic: 2, Ghost: 2, Dark: 0.5, Fairy: 0.5 },
  Steel:    { Fire: 0.5, Water: 0.5, Electric: 0.5, Ice: 2, Rock: 2, Steel: 0.5, Fairy: 2 },
  Fairy:    { Fire: 0.5, Fighting: 2, Poison: 0.5, Dragon: 2, Dark: 2, Steel: 0.5 },
};

export const TYPE_FR: Record<string, string> = {
  Normal:   "Normal",
  Fire:     "Feu",
  Water:    "Eau",
  Grass:    "Plante",
  Electric: "Électrik",
  Ice:      "Glace",
  Fighting: "Combat",
  Poison:   "Poison",
  Ground:   "Sol",
  Flying:   "Vol",
  Psychic:  "Psy",
  Bug:      "Insecte",
  Rock:     "Roche",
  Ghost:    "Spectre",
  Dragon:   "Dragon",
  Dark:     "Ténèbres",
  Steel:    "Acier",
  Fairy:    "Fée",
};

export const ALL_TYPES = [
  "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
  "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
  "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
] as const;

export type GameType = (typeof ALL_TYPES)[number];

/** Multiplier for attackingType hitting a single defender type. */
export function effectiveness(attacking: string, defending: string): number {
  return offensiveChart[attacking]?.[defending] ?? 1;
}

/** Multiplier for attackingType hitting a dual-type defender. */
export function effectivenessDual(attacking: string, def1: string, def2: string | null): number {
  const m1 = effectiveness(attacking, def1);
  const m2 = def2 ? effectiveness(attacking, def2) : 1;
  return m1 * m2;
}

export interface CoverageEntry {
  type1: string;
  type2: string | null;
  multiplier: number; // best multiplier from all attacking types combined
}

/**
 * Given a set of attacking move types, compute max multiplier against every
 * single-type and dual-type combination (18 + 153 = 171 combos).
 * Returns only entries where best multiplier >= threshold (default 2).
 */
export function computeOffensiveCoverage(
  attackingTypes: string[],
  threshold = 2,
): CoverageEntry[] {
  const results: CoverageEntry[] = [];

  for (let i = 0; i < ALL_TYPES.length; i++) {
    const t1 = ALL_TYPES[i];
    // Single-type
    const best1 = Math.max(...attackingTypes.map((a) => effectivenessDual(a, t1, null)));
    if (best1 >= threshold) results.push({ type1: t1, type2: null, multiplier: best1 });

    for (let j = i + 1; j < ALL_TYPES.length; j++) {
      const t2 = ALL_TYPES[j];
      const bestDual = Math.max(...attackingTypes.map((a) => effectivenessDual(a, t1, t2)));
      if (bestDual >= threshold) results.push({ type1: t1, type2: t2, multiplier: bestDual });
    }
  }

  return results;
}
