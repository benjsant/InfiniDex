import type { Metadata } from "next";
import type { ReactNode } from "react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fusiondex.app";

export const metadata: Metadata = {
  title: "Top 50 Fusions BST — InfiniDex",
  description:
    "Classement des 50 fusions Pokémon Infinite Fusion avec le BST (Base Stat Total) le plus élevé, parmi toutes les combinaisons possibles.",
  openGraph: {
    title: "Top 50 Fusions BST",
    description: "Les meilleures fusions Pokémon Infinite Fusion classées par BST.",
    url: `${SITE_URL}/fusion/top`,
    siteName: "InfiniDex",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Top 50 Fusions BST — InfiniDex",
    description: "Les meilleures fusions Pokémon Infinite Fusion classées par BST.",
  },
  alternates: { canonical: `${SITE_URL}/fusion/top` },
};

interface TopFusionItem {
  rank: number;
  head_id: number;
  body_id: number;
  head_name_en: string;
  body_name_en: string;
  bst: number;
}

async function fetchTop50(): Promise<TopFusionItem[]> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/fusions/top?limit=50`, {
      headers,
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function TopFusionsLayout({ children }: { children: ReactNode }) {
  const top50 = await fetchTop50();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Top 50 Fusions BST — Pokémon Infinite Fusion",
    description:
      "Les 50 meilleures fusions Pokémon Infinite Fusion classées par BST total.",
    url: `${SITE_URL}/fusion/top`,
    numberOfItems: top50.length,
    itemListElement: top50.map((f) => ({
      "@type": "ListItem",
      position: f.rank,
      name: `${f.head_name_en}/${f.body_name_en}`,
      url: `${SITE_URL}/fusion/${f.head_id}/${f.body_id}`,
      description: `BST ${f.bst}`,
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {children}
    </>
  );
}
