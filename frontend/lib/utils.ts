import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { STAT_LABELS, CATEGORY_LABELS, METHOD_LABELS } from "./constants";

// Re-export statColor so components can import from either place
export { statColor } from "./constants";
import type { PokemonTypeSlot } from "@/types/api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatStatName(key: string): string {
  return STAT_LABELS[key] ?? key;
}

export function formatCategory(cat: string | null): string {
  if (!cat) return "—";
  return CATEGORY_LABELS[cat] ?? cat;
}

export function formatMethod(method: string): string {
  return METHOD_LABELS[method] ?? method;
}

export function formatPower(power: number | null): string {
  return power != null ? String(power) : "—";
}

export function formatAccuracy(acc: number | null): string {
  return acc != null ? `${acc}%` : "—";
}

// Normalize for accent-insensitive search (mirrors backend normalize())
export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function statBarWidth(value: number, max = 255): number {
  return Math.min(100, Math.round((value / max) * 100));
}

// Helpers for types list from Pokemon
export function primaryType(types: PokemonTypeSlot[]): PokemonTypeSlot | undefined {
  return types.find((t) => t.slot === 1) ?? types[0];
}

export function secondaryType(types: PokemonTypeSlot[]): PokemonTypeSlot | undefined {
  return types.find((t) => t.slot === 2);
}

// Weakness multiplier display
export function multiplierLabel(m: number): string {
  const n = Number(m);
  if (n === 0)     return "×0";
  if (n <= 0.125)  return "×⅛";
  if (n === 0.25)  return "×¼";
  if (n === 0.5)   return "×½";
  if (n === 2)     return "×2";
  if (n === 4)     return "×4";
  if (n === 8)     return "×8";
  return `×${n}`;
}

export function multiplierColor(m: number): string {
  const n = Number(m);
  if (n === 0)   return "bg-gray-700 text-gray-300";
  if (n < 1)     return "bg-green-700 text-green-100";
  if (n === 2)   return "bg-red-600 text-red-100";
  if (n >= 4)    return "bg-red-900 text-red-100";
  return "bg-gray-500 text-white";
}
