import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FusionDex — Pokémon Infinite Fusion",
    short_name: "FusionDex",
    description:
      "Pokédex intelligent pour Pokémon Infinite Fusion — fusions, stats, IA.",
    start_url: "/fusion",
    display: "standalone",
    background_color: "#090c1a",
    theme_color: "#6366f1",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
