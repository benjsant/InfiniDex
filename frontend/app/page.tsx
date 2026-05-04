import Link from "next/link";
import { BookOpen, GitMerge, Zap, Shield, Star, Bot, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const NAV_CARDS: { href: string; label: string; desc: string; Icon: LucideIcon }[] = [
  { href: "/pokedex",        label: "Pokédex",        desc: "501 Pokémon IF",                    Icon: BookOpen  },
  { href: "/fusion",         label: "Fusion",         desc: "Calcule n'importe quelle fusion",   Icon: GitMerge  },
  { href: "/moves",          label: "Capacités",      desc: "Toutes les attaques IF",            Icon: Zap       },
  { href: "/types",          label: "Types",          desc: "Tableau d'efficacités Gen 7",       Icon: Shield    },
  { href: "/abilities",      label: "Talents",        desc: "Tous les talents IF",               Icon: Star      },
  { href: "/ai",             label: "Assistant IA",   desc: "Pose tes questions sur IF",         Icon: Bot       },
  { href: "/triple-fusions", label: "Triple Fusions", desc: "Les fusions légendaires secrètes", Icon: Layers    },
];

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4 text-center">
      <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
        FusionDex
      </h1>
      <p className="text-xl text-if-text-lo mb-2 max-w-xl">
        Le Pokédex intelligent pour{" "}
        <span className="text-indigo-400 font-semibold">Pokémon Infinite Fusion</span>
      </p>
      <p className="text-sm text-if-text-xs mb-10 max-w-lg">
        501 Pokémon · Calculateur de fusions · Assistant IA · Types IF
      </p>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 w-full max-w-3xl">
        {NAV_CARDS.map(({ href, label, desc, Icon }) => (
          <NavCard key={href} href={href} label={label} desc={desc} Icon={Icon} />
        ))}
      </div>
    </div>
  );
}

function NavCard({ href, label, desc, Icon }: { href: string; label: string; desc: string; Icon: LucideIcon }) {
  return (
    <Link
      href={href}
      className="group flex flex-col items-start gap-2 p-4 rounded-xl bg-if-card border border-if-border-mid hover:border-indigo-500 hover:bg-if-elevated transition-all duration-200"
    >
      <Icon size={20} className="text-indigo-400 group-hover:text-indigo-300 transition-colors" />
      <span className="font-semibold text-if-text-hi group-hover:text-indigo-400 transition-colors">
        {label}
      </span>
      <span className="text-xs text-if-text-xs text-left">{desc}</span>
    </Link>
  );
}
