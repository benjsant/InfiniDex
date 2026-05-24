import type { Metadata } from "next";
import type { ReactNode } from "react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.INFINIDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://infinidex.app";

interface FusionMeta {
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
  type1: { name_en: string; name_fr: string | null } | null;
  type2: { name_en: string; name_fr: string | null } | null;
  sprite_path: string;
}

async function fetchFusionMeta(
  headId: number,
  bodyId: number,
): Promise<FusionMeta | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/fusion/${headId}/${bodyId}`, {
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
  params: Promise<{ headId: string; bodyId: string }>;
}): Promise<Metadata> {
  const { headId, bodyId } = await params;
  const f = await fetchFusionMeta(parseInt(headId, 10), parseInt(bodyId, 10));
  if (!f) return { title: "Fusion — InfiniDex" };

  const fusionName = `${f.head_name_en}/${f.body_name_en}`;
  const bst = f.hp + f.attack + f.defense + f.sp_attack + f.sp_defense + f.speed;
  const types = [f.type1?.name_en, f.type2?.name_en].filter(Boolean).join("/");
  const description = `Fusion ${fusionName} — Type ${types || "?"} · BST ${bst}. Stats, capacités et sprites dans Pokémon Infinite Fusion.`;
  const url = `${SITE_URL}/fusion/${f.head_id}/${f.body_id}`;

  return {
    title: `${fusionName} — InfiniDex`,
    description,
    openGraph: {
      title: `${fusionName} — Fusion PIF`,
      description,
      url,
      siteName: "InfiniDex",
      type: "website",
      images: f.sprite_path
        ? [{ url: `${SITE_URL}${f.sprite_path}`, width: 288, height: 288, alt: fusionName }]
        : [],
    },
    twitter: {
      card: f.sprite_path ? "summary_large_image" : "summary",
      title: `${fusionName} — InfiniDex`,
      description,
    },
    alternates: { canonical: url },
  };
}

export default async function FusionDetailLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ headId: string; bodyId: string }>;
}) {
  const { headId, bodyId } = await params;
  const f = await fetchFusionMeta(parseInt(headId, 10), parseInt(bodyId, 10));

  if (!f) return <>{children}</>;

  const fusionName = `${f.head_name_en}/${f.body_name_en}`;
  const bst = f.hp + f.attack + f.defense + f.sp_attack + f.sp_defense + f.speed;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Thing",
    name: fusionName,
    description: `Fusion de ${f.head_name_en} (tête) et ${f.body_name_en} (corps) dans Pokémon Infinite Fusion. Type ${[f.type1?.name_en, f.type2?.name_en].filter(Boolean).join("/")}. BST ${bst}.`,
    url: `${SITE_URL}/fusion/${f.head_id}/${f.body_id}`,
    image: f.sprite_path ? `${SITE_URL}${f.sprite_path}` : undefined,
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
