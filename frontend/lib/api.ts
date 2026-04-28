import { API_BASE_URL } from "./constants";
import type {
  PokemonListItem,
  PokemonDetail,
  PokemonMoveOut,
  EvolutionOut,
  WeaknessOut,
  TypeOut,
  MoveListItem,
  MoveDetail,
  AbilityListItem,
  AbilityDetail,
  FusionResult,
  SpriteOut,
  FusionMoveOut,
  FusionExpertMoveOut,
  AiRequest,
  AiProviderInfo,
} from "@/types/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status} — ${path}`);
  }
  return res.json() as Promise<T>;
}

// ── Pokémon ──────────────────────────────────────────────────────────────────

export function getPokemonList(params?: {
  type_id?: number;
  gen?: number;
  page?: number;
  page_size?: number;
}): Promise<PokemonListItem[]> {
  const sp = new URLSearchParams();
  if (params?.type_id)   sp.set("type_id", String(params.type_id));
  if (params?.gen)       sp.set("generation_id", String(params.gen));
  const pageSize = params?.page_size ?? 40;
  sp.set("limit", String(pageSize));
  if (params?.page && params.page > 1) {
    sp.set("offset", String((params.page - 1) * pageSize));
  }
  const qs = sp.toString() ? `?${sp}` : "";
  return apiFetch<PokemonListItem[]>(`/pokemon/${qs}`);
}

export function searchPokemon(q: string): Promise<PokemonListItem[]> {
  return apiFetch<PokemonListItem[]>(`/pokemon/search?q=${encodeURIComponent(q)}`);
}

export function getPokemon(id: number): Promise<PokemonDetail> {
  return apiFetch<PokemonDetail>(`/pokemon/${id}`);
}

export function getPokemonMoves(id: number): Promise<PokemonMoveOut[]> {
  return apiFetch<PokemonMoveOut[]>(`/pokemon/${id}/moves`);
}

export function getPokemonEvolutions(id: number): Promise<EvolutionOut[]> {
  return apiFetch<EvolutionOut[]>(`/pokemon/${id}/evolutions`);
}

export function getPokemonWeaknesses(id: number): Promise<WeaknessOut[]> {
  return apiFetch<WeaknessOut[]>(`/pokemon/${id}/weaknesses`);
}

// ── Fusion ───────────────────────────────────────────────────────────────────

export function getFusion(headId: number, bodyId: number): Promise<FusionResult> {
  return apiFetch<FusionResult>(`/fusion/${headId}/${bodyId}`);
}

export function getFusionMoves(headId: number, bodyId: number): Promise<FusionMoveOut[]> {
  return apiFetch<FusionMoveOut[]>(`/fusion/${headId}/${bodyId}/moves`);
}

export function getFusionExpertMoves(headId: number, bodyId: number): Promise<FusionExpertMoveOut[]> {
  return apiFetch<FusionExpertMoveOut[]>(`/fusion/${headId}/${bodyId}/expert-moves`);
}

export function getSprites(headId: number, bodyId: number): Promise<SpriteOut[]> {
  return apiFetch<SpriteOut[]>(`/sprites/${headId}/${bodyId}`);
}

// ── Moves ────────────────────────────────────────────────────────────────────

export function getMoves(): Promise<MoveListItem[]> {
  return apiFetch<MoveListItem[]>("/moves");
}

export function getMove(id: number): Promise<MoveDetail> {
  return apiFetch<MoveDetail>(`/moves/${id}`);
}

export function searchMoves(q: string): Promise<MoveListItem[]> {
  return apiFetch<MoveListItem[]>(`/moves/search?q=${encodeURIComponent(q)}`);
}

export function getMovesByType(typeName: string): Promise<MoveListItem[]> {
  return apiFetch<MoveListItem[]>(`/moves/by-type/${encodeURIComponent(typeName)}`);
}

// ── Abilities ────────────────────────────────────────────────────────────────

export function getAbilities(): Promise<AbilityListItem[]> {
  return apiFetch<AbilityListItem[]>("/abilities");
}

export function getAbility(id: number): Promise<AbilityDetail> {
  return apiFetch<AbilityDetail>(`/abilities/${id}`);
}

export function searchAbilities(q: string): Promise<AbilityListItem[]> {
  return apiFetch<AbilityListItem[]>(`/abilities/search?q=${encodeURIComponent(q)}`);
}

// ── Types ────────────────────────────────────────────────────────────────────

export function getTypes(): Promise<TypeOut[]> {
  return apiFetch<TypeOut[]>("/types");
}

// ── AI (streaming) ───────────────────────────────────────────────────────────

export async function askAi(req: AiRequest): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}/ai/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`AI error ${res.status}`);
  return res;
}

export function getAiProvider(): Promise<AiProviderInfo> {
  return apiFetch<AiProviderInfo>("/ai/provider");
}
