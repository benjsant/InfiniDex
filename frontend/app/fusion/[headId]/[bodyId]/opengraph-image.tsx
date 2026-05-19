import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Fusion Pokémon Infinite Fusion";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

async function fetchMeta(headId: number, bodyId: number) {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/fusion/${headId}/${bodyId}`, { headers });
    if (!res.ok) return null;
    return res.json() as Promise<{
      head_name_en: string;
      body_name_en: string;
      type1: { name_en: string } | null;
      type2: { name_en: string } | null;
      hp: number; attack: number; defense: number;
      sp_attack: number; sp_defense: number; speed: number;
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
  params: Promise<{ headId: string; bodyId: string }>;
}) {
  const { headId, bodyId } = await params;
  const hId = parseInt(headId, 10);
  const bId = parseInt(bodyId, 10);
  const fusion = await fetchMeta(hId, bId);

  const name = fusion
    ? `${fusion.head_name_en}/${fusion.body_name_en}`
    : `Fusion #${hId}/#${bId}`;
  const bst = fusion
    ? fusion.hp + fusion.attack + fusion.defense + fusion.sp_attack + fusion.sp_defense + fusion.speed
    : null;
  const types = fusion
    ? [fusion.type1?.name_en, fusion.type2?.name_en].filter(Boolean).join(" / ")
    : "";

  const spriteSrc = await fetchSpriteDataUrl(`${BACKEND_URL}/sprites/${hId}/${bId}/image`);

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
          background: "linear-gradient(135deg, #090c1a 0%, #111428 60%, #1a1040 100%)",
          fontFamily: "sans-serif",
          gap: 24,
        }}
      >
        {/* Sprite */}
        {spriteSrc && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={spriteSrc}
            alt={name}
            width={200}
            height={200}
            style={{ imageRendering: "pixelated" }}
          />
        )}

        {/* Name */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 64, fontWeight: 800, color: "#e8e8ff", letterSpacing: -2 }}>
            {name}
          </span>
          {types && (
            <span style={{ fontSize: 28, color: "#818cf8", fontWeight: 600 }}>{types}</span>
          )}
          {bst !== null && (
            <span style={{ fontSize: 22, color: "#6b7199", fontWeight: 500 }}>
              BST {bst}
            </span>
          )}
        </div>

        {/* Watermark */}
        <span style={{ position: "absolute", bottom: 24, right: 36, fontSize: 18, color: "#2d3260" }}>
          InfiniDex
        </span>
      </div>
    ),
    { ...size },
  );
}
