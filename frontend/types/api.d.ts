// Mirror of backend Pydantic schemas — aligned with actual API responses

export interface ItemOut {
  id: number;
  name_en: string;
  name_fr: string | null;
  category: "fusion" | "evolution" | "valuable";
  effect: string | null;
  price_buy: number | null;
  price_sell: number | null;
}

export interface GenerationOut {
  id: number;
  name_en: string;
  name_fr: string;
}

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
  pokepedia_url: string | null;
  bst: number;
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
  bst: number;
  base_experience: number | null;
  is_hoenn_only: boolean;
  sprite_path: string | null;
  pokepedia_url: string | null;
  types: PokemonTypeSlot[];
  abilities: PokemonAbilitySlot[];
}

export interface PokemonMoveOut {
  move_id: number;
  name_en: string;
  name_fr: string | null;
  category: string;
  power: number | null;
  accuracy: number | null;
  pp: number;
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
  pokemon_national_id: number | null;
  evolves_into_id: number;
  evolves_into_name_en: string;
  evolves_into_name_fr: string | null;
  evolves_into_national_id: number | null;
  trigger_type: string;
  min_level: number | null;
  item_name_en: string | null;
  item_name_fr: string | null;
  if_override: boolean;
  if_notes: string | null;
}

export interface LocationOut {
  location_id: number;
  location_name: string;
  method: string;
  notes: string | null;
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
  category: string;
  power: number | null;
  accuracy: number | null;
  pp: number;
}

export interface TMLocationOut {
  location_id: number;
  location_name_en: string;
  location_name_fr: string | null;
  notes: string | null;
}

export interface TMInfo {
  number: number;
  location_summary: string | null;
  locations: TMLocationOut[];
}

export interface MoveDetail extends MoveListItem {
  description_en: string | null;
  description_fr: string | null;
  source: string;
  tm: TMInfo | null;
}

export interface AbilityListItem {
  id: number;
  name_en: string;
  name_fr: string | null;
}

export interface AbilityDetail extends AbilityListItem {
  description_en: string | null;
  description_fr: string | null;
}

export interface FusionAbilityOut {
  ability_id: number;
  name_en: string;
  name_fr: string | null;
  is_hidden: boolean;
  origin: "head" | "body";
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
  type1: TypeOut | null;
  type2: TypeOut | null;
  sprite_path: string;
}

export interface SpriteOut {
  id: number;
  head_id: number;
  body_id: number;
  sprite_path: string;
  is_custom: boolean;
  is_default: boolean;
  source: string;
  creators: string[];
}

export interface FusionInvolvingOut {
  head_id: number;
  body_id: number;
  role: "head" | "body";
  partner_id: number;
  partner_name_en: string | null;
  partner_name_fr: string | null;
}

export interface FusionMoveOut {
  move_id: number;
  name_en: string;
  name_fr: string | null;
  category: string;
  power: number | null;
  accuracy: number | null;
  pp: number;
  type: TypeOut;
  method: string;
  level: number | null;
  source: string;
  origin: "head" | "body" | "both";
}

export interface FusionExpertMoveOut {
  move_id: number;
  name_en: string;
  name_fr: string | null;
  category: string;
  power: number | null;
  accuracy: number | null;
  pp: number;
  type: TypeOut;
  locations: string[];
  prices_heart_scales: Record<string, number>;
}

export interface TripleFusionTypeOut {
  slot: number;
  name_en: string;
  name_fr: string | null;
  is_triple_fusion_type: boolean;
}

export interface TripleFusionComponentOut {
  position: number;
  pokemon_id: number;
  name_en: string;
  name_fr: string | null;
}

export interface TripleFusionAbilityOut {
  slot: number;
  is_hidden: boolean;
  name_en: string;
  name_fr: string | null;
}

export interface TripleFusionListItem {
  id: number;
  name_en: string;
  name_fr: string | null;
  sprite_path: string | null;
  types: TripleFusionTypeOut[];
}

export interface TripleFusionDetail extends TripleFusionListItem {
  hp: number;
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
  evolves_from_id: number | null;
  evolution_level: number | null;
  steps_to_hatch: number | null;
  components: TripleFusionComponentOut[];
  abilities: TripleFusionAbilityOut[];
}

export interface MoveTutorOut {
  id: number;
  move_id: number;
  move_name_en: string;
  move_name_fr: string | null;
  location_id: number;
  location_name_en: string;
  location_name_fr: string | null;
  price: number | null;
  currency: "pokedollars" | "free" | "quest";
  npc_description: string | null;
}

export interface MoveExpertOut {
  move_id: number;
  move_name_en: string;
  move_name_fr: string | null;
  location: "knot_island" | "boon_island";
  required_pokemon: string[];
  required_types: string[];
}

export interface CreatorOut {
  id: number;
  name: string;
  sprite_count: number;
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
