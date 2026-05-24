import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Top 50 Fusions — InfiniDex";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
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
          background: "linear-gradient(135deg, #090c1a 0%, #0f1430 60%, #1a1040 100%)",
          fontFamily: "sans-serif",
          gap: 24,
        }}
      >
        {/* Trophy icon representation */}
        <div style={{ fontSize: 64 }}>🏆</div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 52, fontWeight: 900, color: "#e8b84b", letterSpacing: "-1px" }}>
            Top 50 Fusions
          </div>
          <div style={{ fontSize: 26, color: "#818cf8", fontWeight: 600 }}>
            Classement BST — Pokémon Infinite Fusion
          </div>
          <div style={{ fontSize: 18, color: "#a0a0b4", marginTop: 8 }}>
            Les meilleures combinaisons tête × corps parmi 251 001 possibilités
          </div>
        </div>

        <div
          style={{
            position: "absolute",
            bottom: 24,
            right: 32,
            fontSize: 16,
            color: "#2d3260",
          }}
        >
          infinidex.app
        </div>
      </div>
    ),
    { ...size },
  );
}
