// Mirror of backend Pydantic schemas — aligned with actual API responses

// TypeOut from type_.py (used in Move, Fusion)
export interface TypeOut {
  id: number;
  name_en: string;
  name_fr: string | null;
  is_triple_fusion_type: boolean;
}

// TypeSlot from pokemon.py (used in PokemonListItem / PokemonDetail)
export interface PokemonTypeSlot {
  slot: number;
  name_en: string;
  name_fr: string | null;
}

export interface PokemonAbilitySlot {
  slot: number;
  is_hidden: boolean;
  name_en: string;
  name_fr: string | null;
}

export interface PokemonListItem {
  id: number;
  national_id: number | null;
  name_en: string;
  name_fr: string | null;
  types: PokemonTypeSlot[];
  sprite_path: string | null;
  is_hoenn_only: boolean;
}

export interface PokemonDetail {
  id: number;
  national_id: number | null;
  name_en: string;
  name_fr: string | null;
  generation_id: number;
  hp: number;
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
  base_experience: number | null;
  is_hoenn_only: boolean;
  sprite_path: string | null;
  types: PokemonTypeSlot[];
  abilities: PokemonAbilitySlot[];
}

export interface PokemonMoveOut {
  move_id: number;
  name_en: string;
  name_fr: string | null;
  category: string | null;
  power: number | null;
  accuracy: number | null;
  pp: number | null;
  type: TypeOut;
  method: string;
  level: number | null;
  source: string;
}

export interface EvolutionOut {
  id: number;
  pokemon_id: number;
  pokemon_name_en: string | null;
  pokemon_name_fr: string | null;
  evolves_into_id: number;
  evolves_into_name_en: string;
  evolves_into_name_fr: string | null;
  trigger_type: string;
  min_level: number | null;
  item_name_en: string | null;
  item_name_fr: string | null;
  if_override: boolean;
  if_notes: string | null;
}

export interface WeaknessOut {
  attacking_type_id: number;
  attacking_type_name_en: string;
  attacking_type_name_fr: string | null;
  multiplier: number;
}

export interface MoveListItem {
  id: number;
  name_en: string;
  name_fr: string | null;
  type: TypeOut;
  category: string | null;
  power: number | null;
  accuracy: number | null;
  pp: number | null;
}

export interface MoveDetail extends MoveListItem {
  description_en: string | null;
  description_fr: string | null;
  source: string;
}

export interface AbilityListItem {
  id: number;
  name_en: string;
  name_fr: string | null;
}

export interface AbilityDetail extends AbilityListItem {
  description_en: string | null;
  description_fr: string | null;
  if_modified: boolean;
  if_notes: string | null;
}

// FusionResult — stats are flat (not nested), types are TypeOut objects
export interface FusionResult {
  head_id: number;
  body_id: number;
  head_name_en: string;
  head_name_fr: string | null;
  body_name_en: string;
  body_name_fr: string | null;
  hp: number;
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
  type1: TypeOut;
  type2: TypeOut | null;
  sprite_path: string;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AiRequest {
  message: string;
  context?: string;
  history?: HistoryMessage[];
}

export interface AiProviderInfo {
  name: string;
  model: string;
}
