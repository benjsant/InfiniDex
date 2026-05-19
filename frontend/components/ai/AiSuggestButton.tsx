"use client";

import Link from "next/link";
import { Bot } from "lucide-react";

interface AiSuggestButtonProps {
  pokemonName: string;
  pokemonId: number;
  context?: string;
  question?: string;
}

export function AiSuggestButton({ pokemonName, pokemonId, context, question }: AiSuggestButtonProps) {
  const defaultQuestion = `Quels sont les meilleurs partenaires de fusion pour ${pokemonName} (#${pokemonId}) dans Pokémon Infinite Fusion ? Donne des conseils stratégiques.`;
  const query = encodeURIComponent(question ?? defaultQuestion);

  const href = context
    ? `/ai?q=${query}&ctx=${encodeURIComponent(context)}`
    : `/ai?q=${query}`;

  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-700/30 border border-indigo-600/40 text-indigo-300 hover:bg-indigo-700/50 hover:text-indigo-200 transition-all text-sm font-medium"
    >
      <Bot size={14} /> Demander à l&apos;IA
    </Link>
  );
}
