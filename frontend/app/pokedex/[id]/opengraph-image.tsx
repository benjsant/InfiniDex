import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Pokémon Infinite Fusion";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

async function fetchMeta(id: number) {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/pokemon/${id}`, { headers });
    if (!res.ok) return null;
    return res.json() as Promise<{
      id: number;
      national_id: number | null;
      name_en: string;
      name_fr: string | null;
      hp: number; attack: number; defense: number;
      sp_attack: number; sp_defense: number; speed: number;
      sprite_path: string | null;
      types: { slot: number; name_en: string; name_fr: string | null }[];
    }>;
  } catch {
    return null;
  }
}

// Satori fetches <img src> without our headers, so the key-protected sprite
// endpoint 403s. Pre-fetch it server-side with the key and inline as a data URL.
async function fetchSpriteDataUrl(url: string): Promise<string | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(url, { headers });
    if (!res.ok) return null;
    const bytes = new Uint8Array(await res.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return `data:image/png;base64,${btoa(binary)}`;
  } catch {
    return null;
  }
}

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const p = await fetchMeta(parseInt(id, 10));

  const name = p ? (p.name_fr ?? p.name_en) : `Pokémon #${id}`;
  const nameEn = p?.name_fr ? p.name_en : null;
  const bst = p ? p.hp + p.attack + p.defense + p.sp_attack + p.sp_defense + p.speed : null;
  const types = p ? p.types.map((t) => t.name_fr ?? t.name_en).join(" / ") : "";
  const spriteSrc = p ? await fetchSpriteDataUrl(`${BACKEND_URL}/sprites/${p.id}/${p.id}/image`) : null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #090c1a 0%, #111428 60%, #0f0a30 100%)",
          fontFamily: "sans-serif",
          gap: 20,
        }}
      >
        {spriteSrc && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={spriteSrc} alt={name} width={180} height={180} style={{ imageRendering: "pixelated" }} />
        )}

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          {p && (
            <span style={{ fontSize: 22, color: "#6b7199", fontWeight: 500 }}>
              IF #{String(p.id).padStart(3, "0")}
              {p.national_id ? ` · National #${String(p.national_id).padStart(3, "0")}` : ""}
            </span>
          )}
          <span style={{ fontSize: 72, fontWeight: 800, color: "#e8e8ff", letterSpacing: -2 }}>
            {name}
          </span>
          {nameEn && (
            <span style={{ fontSize: 30, color: "#6b7199" }}>{nameEn}</span>
          )}
          {types && (
            <span style={{ fontSize: 28, color: "#818cf8", fontWeight: 600 }}>{types}</span>
          )}
          {bst !== null && (
            <span style={{ fontSize: 22, color: "#4a4f75" }}>BST {bst}</span>
          )}
        </div>

        <span style={{ position: "absolute", bottom: 24, right: 36, fontSize: 18, color: "#2d3260" }}>
          InfiniDex
        </span>
      </div>
    ),
    { ...size },
  );
}
