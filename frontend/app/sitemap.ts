import type { MetadataRoute } from "next";

const SITE_URL  = process.env.NEXT_PUBLIC_SITE_URL   ?? "https://fusiondex.app";
const BACKEND   = process.env.BACKEND_INTERNAL_URL   ?? `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;
const IKEY      = process.env.INTERNAL_API_KEY       ?? "";

const STATIC_ROUTES = [
  "/",
  "/fusion",
  "/fusion/top",
  "/pokedex",
  "/moves",
  "/abilities",
  "/items",
  "/types",
  "/fusion/compare",
];

async function fetchTopFusionPairs(): Promise<{ headId: number; bodyId: number }[]> {
  try {
    const headers: Record<string, string> = {};
    if (IKEY) headers["X-Internal-Key"] = IKEY;
    const res = await fetch(`${BACKEND}/fusions/top?limit=50`, {
      headers,
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { head_id: number; body_id: number }[] = await res.json();
    return data.map((f) => ({ headId: f.head_id, bodyId: f.body_id }));
  } catch {
    return [];
  }
}

async function fetchPokemonIds(): Promise<number[]> {
  try {
    const headers: Record<string, string> = {};
    if (IKEY) headers["X-Internal-Key"] = IKEY;
    const res = await fetch(`${BACKEND}/pokemon/?limit=600&include_hoenn=true`, {
      headers,
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { id: number }[] = await res.json();
    return data.map((p) => p.id);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const [pokemonIds, topFusions] = await Promise.all([
    fetchPokemonIds(),
    fetchTopFusionPairs(),
  ]);

  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: route === "/" || route === "/fusion" ? "daily" : "weekly",
    priority: route === "/" ? 1.0 : route === "/fusion" ? 0.9 : 0.7,
  }));

  const pokemonEntries: MetadataRoute.Sitemap = pokemonIds.map((id) => ({
    url: `${SITE_URL}/pokedex/${id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const fusionEntries: MetadataRoute.Sitemap = topFusions.map(({ headId, bodyId }) => ({
    url: `${SITE_URL}/fusion/${headId}/${bodyId}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.65,
  }));

  return [...staticEntries, ...pokemonEntries, ...fusionEntries];
}
