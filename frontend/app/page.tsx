import Link from "next/link";
import { BookOpen, GitMerge, Zap, Shield, Star, Bot, Layers, Package, Shuffle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.INFINIDEX_BACKEND_PORT ?? "58000"}`;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

interface CoverageStats {
  pokemon_total: number;
  fusion_sprites_total: number;
  triple_fusions_total: number;
  creators_total: number;
}

async function fetchStats(): Promise<CoverageStats | null> {
  try {
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) headers["X-Internal-Key"] = INTERNAL_API_KEY;
    const res = await fetch(`${BACKEND_URL}/stats/coverage`, {
      headers,
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

const NAV_CARDS: { href: string; label: string; desc: string; Icon: LucideIcon; accent?: boolean }[] = [
  { href: "/fusion",         label: "Calculateur de fusion", desc: "Combine n'importe quels deux Pokémon",  Icon: GitMerge, accent: true },
  { href: "/pokedex",        label: "Pokédex",               desc: "501 Pokémon IF avec stats complètes",  Icon: BookOpen  },
  { href: "/ai",             label: "Assistant IA",          desc: "Stratégie, builds, conseils",          Icon: Bot       },
  { href: "/moves",          label: "Capacités",             desc: "Toutes les attaques Infinite Fusion",  Icon: Zap       },
  { href: "/types",          label: "Types",                 desc: "Tableau d'efficacités Gen 7",          Icon: Shield    },
  { href: "/abilities",      label: "Talents",               desc: "Tous les talents IF",                  Icon: Star      },
  { href: "/items",          label: "Objets",                desc: "Fusion, évolution, précieux",          Icon: Package   },
  { href: "/triple-fusions", label: "Triple Fusions",        desc: "Les fusions légendaires secrètes",     Icon: Layers    },
];

export default async function HomePage() {
  const stats = await fetchStats();
  const pokemonTotal = stats?.pokemon_total ?? 501;
  const possibleFusions = pokemonTotal * pokemonTotal;
  const customSprites = stats?.fusion_sprites_total ?? null;
  const creators = stats?.creators_total ?? null;

  const STAT_CHIPS: { label: string; value: string }[] = [
    { label: "Pokémon IF",       value: pokemonTotal.toLocaleString("fr-FR") },
    { label: "Fusions possibles", value: possibleFusions.toLocaleString("fr-FR") },
    ...(customSprites !== null ? [{ label: "Sprites customs", value: customSprites.toLocaleString("fr-FR") }] : []),
    ...(creators !== null ? [{ label: "Créateurs", value: creators.toLocaleString("fr-FR") }] : []),
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-16">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-5xl sm:text-6xl font-bold mb-3 bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-300 bg-clip-text text-transparent">
          InfiniDex
        </h1>
        <p className="text-lg sm:text-xl text-if-text-lo mb-6 max-w-lg mx-auto">
          Le Pokédex intelligent pour{" "}
          <span className="text-indigo-400 font-semibold">Pokémon Infinite Fusion</span>
        </p>

        {/* Live stats chips */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {STAT_CHIPS.map(({ label, value }) => (
            <div
              key={label}
              className="flex flex-col items-center px-4 py-2 rounded-xl"
              style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)" }}
            >
              <span className="text-xl font-bold font-mono text-indigo-300">{value}</span>
              <span className="text-[11px] text-if-muted">{label}</span>
            </div>
          ))}
        </div>

        {/* Primary CTA */}
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            href="/fusion"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm transition-all"
            style={{ background: "#6366f1", color: "#fff" }}
          >
            <GitMerge size={16} />
            Calculer une fusion
          </Link>
          <Link
            href="/fusion/random"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm transition-all"
            style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-text-lo)" }}
          >
            <Shuffle size={16} />
            Fusion aléatoire
          </Link>
        </div>
      </div>

      {/* Nav grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {NAV_CARDS.map(({ href, label, desc, Icon, accent }) => (
          <NavCard key={href} href={href} label={label} desc={desc} Icon={Icon} accent={accent} />
        ))}
      </div>
    </div>
  );
}

function NavCard({
  href, label, desc, Icon, accent,
}: {
  href: string; label: string; desc: string; Icon: LucideIcon; accent?: boolean;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col items-start gap-2 p-4 rounded-xl transition-all duration-200"
      style={{
        background: accent ? "rgba(99,102,241,0.10)" : "var(--color-if-card)",
        border: `1px solid ${accent ? "#6366f166" : "var(--color-if-border)"}`,
      }}
    >
      <Icon
        size={20}
        style={{ color: accent ? "#818cf8" : "#6366f1" }}
        className="group-hover:scale-110 transition-transform duration-200"
      />
      <span className="font-semibold text-if-text-hi group-hover:text-indigo-300 transition-colors text-sm leading-tight">
        {label}
      </span>
      <span className="text-xs text-if-muted text-left leading-snug">{desc}</span>
    </Link>
  );
}
