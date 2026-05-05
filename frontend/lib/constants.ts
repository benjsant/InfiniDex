// Pokémon type color palette (hex) — keyed by name_en (API language)
export const TYPE_COLORS: Record<string, string> = {
  Normal:    "#A8A878",
  Fire:      "#F08030",
  Water:     "#6890F0",
  Electric:  "#F8D030",
  Grass:     "#78C850",
  Ice:       "#98D8D8",
  Fighting:  "#C03028",
  Poison:    "#A040A0",
  Ground:    "#E0C068",
  Flying:    "#A890F0",
  Psychic:   "#F85888",
  Bug:       "#A8B820",
  Rock:      "#B8A038",
  Ghost:     "#705898",
  Dragon:    "#7038F8",
  Dark:      "#705848",
  Steel:     "#B8B8D0",
  Fairy:     "#EE99AC",
  // French aliases (fallback for display)
  Feu:       "#F08030",
  Eau:       "#6890F0",
  Électrik:  "#F8D030",
  Plante:    "#78C850",
  Glace:     "#98D8D8",
  Combat:    "#C03028",
  Poison_fr: "#A040A0",
  Sol:       "#E0C068",
  Vol:       "#A890F0",
  Psy:       "#F85888",
  Insecte:   "#A8B820",
  Roche:     "#B8A038",
  Spectre:   "#705898",
  Ténèbres:  "#705848",
  Acier:     "#B8B8D0",
  Fée:       "#EE99AC",
};

export function typeColor(typeName: string): string {
  return TYPE_COLORS[typeName] ?? "#888";
}

export function typeTextColor(typeName: string): string {
  const lightTypes = new Set(["Electric", "Ice", "Ground", "Steel", "Électrik", "Glace", "Sol", "Acier"]);
  return lightTypes.has(typeName) ? "#333" : "#fff";
}

// stat color by value
export function statColor(value: number): string {
  if (value >= 100) return "#4ade80";
  if (value >= 60)  return "#facc15";
  return "#f87171";
}

// Stat display names — keys match backend field names exactly
export const STAT_LABELS: Record<string, string> = {
  hp:         "PV",
  attack:     "Attaque",
  defense:    "Défense",
  sp_attack:  "Atk Spé.",
  sp_defense: "Déf Spé.",
  speed:      "Vitesse",
};

export const TYPE_FR_NAMES: Record<string, string> = {
  Normal:   "Normal",
  Fire:     "Feu",
  Water:    "Eau",
  Electric: "Électrik",
  Grass:    "Plante",
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

export const CATEGORY_LABELS: Record<string, string> = {
  Physical: "Physique",
  Special:  "Spéciale",
  Status:   "Statut",
};

export const METHOD_LABELS: Record<string, string> = {
  level_up:         "Niveau",
  tm:               "CT",
  breeding:         "Reproduction",
  tutor:            "Donneur",
  before_evolution: "Pré-évolution",
};

export const AI_TOOL_LABELS: Record<string, string> = {
  get_pokemon:              "Pokémon",
  get_fusion:               "Fusion",
  get_triple_fusion:        "Triple Fusion",
  search_move:              "Capacité",
  get_item:                 "Objet",
  get_move_tutors:          "Tuteurs",
  search_pokemon_locations: "Localisations",
  search_wiki:              "Wiki IF",
};

export const AI_SOURCE_LABELS: Record<string, string> = {
  db:   "Base de données",
  wiki: "Wiki IF",
  web:  "Web",
};

export const AI_SOURCE_COLORS: Record<string, string> = {
  db:   "bg-indigo-950/60 border-indigo-700/50 text-indigo-300",
  wiki: "bg-amber-950/60 border-amber-700/50 text-amber-300",
  web:  "bg-emerald-950/60 border-emerald-700/50 text-emerald-300",
};

// Toutes les requêtes sortent vers la même origine que le frontend. Next.js
// les proxifie vers le backend interne via `rewrites()` (cf. next.config.ts).
// Le browser ne voit jamais l'URL réelle du backend → rien à extraire du bundle.
export const API_BASE_URL = "/api";

export const POKEDEX_PAGE_SIZE = 40;

// Base Pokémon sprites — PokeAPI's public sprites repo (national dex id).
// Long-standing community CDN; avoids redistributing fan-game assets.
export const BASE_SPRITES_URL =
  process.env.NEXT_PUBLIC_BASE_SPRITES_URL ??
  "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon";

export function basePokemonSprite(nationalId: number): string {
  return `${BASE_SPRITES_URL}/${nationalId}.png`;
}
