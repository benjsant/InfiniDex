import type { Metadata } from "next";
import type { ReactNode } from "react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;

const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

async function fetchFusionMeta(
  headId: number,
  bodyId: number,
): Promise<{ headName: string; bodyName: string; type1: string; type2: string | null } | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/fusion/${headId}/${bodyId}`, {
      headers,
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      headName: data.head_name_en,
      bodyName: data.body_name_en,
      type1: data.type1?.name_en ?? "",
      type2: data.type2?.name_en ?? null,
    };
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
  const hId = parseInt(headId, 10);
  const bId = parseInt(bodyId, 10);
  const fusion = await fetchFusionMeta(hId, bId);

  if (!fusion) {
    return { title: "Fusion — FusionDex" };
  }

  const name = `${fusion.headName}/${fusion.bodyName}`;
  const types = [fusion.type1, fusion.type2].filter(Boolean).join("/");
  const description = `Fusion Pokémon Infinite Fusion : ${name}. Type ${types}. Stats, capacités et sprite.`;

  return {
    title: `${name} — FusionDex`,
    description,
    openGraph: {
      title: `${name} — Fusion Pokémon`,
      description,
      type: "website",
    },
    twitter: {
      card: "summary",
      title: `${name} — FusionDex`,
      description,
    },
  };
}

export default function FusionDetailLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
