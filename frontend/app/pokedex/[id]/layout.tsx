import type { Metadata } from "next";
import type { ReactNode } from "react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fusiondex.app";

interface PokemonMeta {
  id: number;
  national_id: number | null;
  name_en: string;
  name_fr: string | null;
  hp: number; attack: number; defense: number;
  sp_attack: number; sp_defense: number; speed: number;
  sprite_path: string | null;
  types: { slot: number; name_en: string; name_fr: string | null }[];
}

async function fetchPokemonMeta(id: number): Promise<PokemonMeta | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/pokemon/${id}`, {
      headers,
      next: { revalidate: 86400 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const p = await fetchPokemonMeta(parseInt(id, 10));
  if (!p) return { title: "Pokémon — FusionDex" };

  const displayName = p.name_fr ?? p.name_en;
  const types = p.types.map((t) => t.name_fr ?? t.name_en).join("/");
  const bst = p.hp + p.attack + p.defense + p.sp_attack + p.sp_defense + p.speed;
  const description = `${displayName} (IF #${p.id}${p.national_id ? `, National #${p.national_id}` : ""}) — Type ${types} · BST ${bst}. Stats, talents, capacités et fusions dans Pokémon Infinite Fusion.`;

  return {
    title: `${displayName} — FusionDex`,
    description,
    openGraph: {
      title: `${displayName} — Pokémon Infinite Fusion`,
      description,
      type: "website",
    },
    twitter: { card: "summary", title: `${displayName} — FusionDex`, description },
  };
}

export default async function PokemonDetailLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const p = await fetchPokemonMeta(parseInt(id, 10));

  const jsonLd = p
    ? {
        "@context": "https://schema.org",
        "@type": "Thing",
        name: p.name_fr ?? p.name_en,
        alternateName: p.name_fr ? p.name_en : undefined,
        description: `Pokémon IF #${p.id}${p.national_id ? ` · National #${p.national_id}` : ""}. Type ${p.types.map((t) => t.name_en).join("/")}. BST ${p.hp + p.attack + p.defense + p.sp_attack + p.sp_defense + p.speed}.`,
        url: `${SITE_URL}/pokedex/${p.id}`,
        image: p.sprite_path ? `${SITE_URL}${p.sprite_path}` : undefined,
      }
    : null;

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      {children}
    </>
  );
}
