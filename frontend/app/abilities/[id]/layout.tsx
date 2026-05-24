import type { Metadata } from "next";
import type { ReactNode } from "react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.INFINIDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://infinidex.app";

interface AbilityMeta {
  id: number;
  name_en: string;
  name_fr: string | null;
  description_en: string | null;
  description_fr: string | null;
}

async function fetchAbilityMeta(id: number): Promise<AbilityMeta | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/abilities/${id}`, {
      headers,
      next: { revalidate: 86400 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateStaticParams() {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/abilities/`, { headers });
    if (!res.ok) return [];
    const data: { id: number }[] = await res.json();
    return data.map((a) => ({ id: String(a.id) }));
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const a = await fetchAbilityMeta(parseInt(id, 10));
  if (!a) return { title: "Talent — InfiniDex" };

  const displayName = a.name_fr ?? a.name_en;
  const description =
    a.description_fr ??
    a.description_en ??
    `${displayName} — talent Pokémon Infinite Fusion.`;

  return {
    title: `${displayName} — InfiniDex`,
    description,
    openGraph: {
      title: `${displayName} — Talent PIF`,
      description,
      url: `${SITE_URL}/abilities/${a.id}`,
      siteName: "InfiniDex",
      type: "website",
    },
    twitter: {
      card: "summary",
      title: `${displayName} — InfiniDex`,
      description,
    },
    alternates: { canonical: `${SITE_URL}/abilities/${a.id}` },
  };
}

export default function AbilityDetailLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
