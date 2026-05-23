"use client";

import Link from "next/link";
import { ExternalLink, Heart } from "lucide-react";
import { usePathname } from "next/navigation";

const NO_FOOTER_PATHS = ["/ai"];

const SOURCES = [
  {
    label: "Pokémon Infinite Fusion",
    href: "https://infinitefusion.fandom.com/wiki/Pok%C3%A9mon_Infinite_Fusion_Wiki",
    desc: "Wiki officiel — données du jeu, mouvements, lieux",
  },
  {
    label: "PokeAPI",
    href: "https://pokeapi.co",
    desc: "Stats, noms FR, évolutions, capacités",
  },
  {
    label: "Pokepedia",
    href: "https://www.pokepedia.fr",
    desc: "Noms et données en français",
  },
  {
    label: "infinitefusion.net",
    href: "https://www.infinitefusion.net",
    desc: "Sprites de fusion (spritesheets)",
  },
  {
    label: "Communauté Sprite Pack",
    href: "https://discord.gg/infinitefusion",
    desc: "Créateurs de sprites custom",
  },
];

export function Footer() {
  const pathname = usePathname();
  if (NO_FOOTER_PATHS.some((p) => pathname?.startsWith(p))) return null;

  return (
    <footer
      className="mt-16 border-t"
      style={{ borderColor: "var(--color-if-border)", background: "var(--color-if-surface)" }}
    >
      <div className="max-w-7xl mx-auto px-4 py-10 grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Colonne projet */}
        <div>
          <p className="text-sm font-semibold mb-2" style={{ color: "var(--color-if-text-hi)" }}>
            InfiniDex
          </p>
          <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--color-if-text-lo)" }}>
            Pokédex intelligent pour{" "}
            <a
              href="https://infinitefusion.fandom.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:opacity-80"
              style={{ color: "var(--color-if-accent)" }}
            >
              Pokémon Infinite Fusion
            </a>
            . Explorez les fusions, découvrez les stats, interrogez l&apos;IA.
          </p>
          <p className="text-xs" style={{ color: "var(--color-if-text-xs)" }}>
            Projet open source —{" "}
            <a
              href="https://github.com/benjsant/InfiniDex"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:opacity-80"
            >
              GitHub
            </a>
          </p>
        </div>

        {/* Colonne sources */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-if-muted)" }}>
            Sources de données
          </p>
          <ul className="space-y-2">
            {SOURCES.map((s) => (
              <li key={s.href} className="flex items-start gap-1.5">
                <ExternalLink size={10} className="mt-0.5 shrink-0" style={{ color: "var(--color-if-muted)" }} />
                <span>
                  <a
                    href={s.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium hover:opacity-80"
                    style={{ color: "var(--color-if-text-dim)" }}
                  >
                    {s.label}
                  </a>
                  <span className="text-xs ml-1" style={{ color: "var(--color-if-text-xs)" }}>
                    — {s.desc}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Colonne crédits */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-if-muted)" }}>
            Remerciements
          </p>
          <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--color-if-text-lo)" }}>
            Un grand merci à l&apos;équipe{" "}
            <a
              href="https://infinitefusion.fandom.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:opacity-80"
              style={{ color: "var(--color-if-accent)" }}
            >
              Pokémon Infinite Fusion
            </a>{" "}
            (Schrroms et toute l&apos;équipe de dev) pour ce jeu fan-made incroyable, ainsi qu&apos;à la
            communauté de{" "}
            <strong style={{ color: "var(--color-if-text-dim)" }}>7 000+ créateurs de sprites</strong>{" "}
            qui font vivre le jeu.
          </p>
          <div className="flex items-center gap-1 mt-4">
            <Link
              href="/about"
              className="text-xs underline underline-offset-2 hover:opacity-80"
              style={{ color: "var(--color-if-text-xs)" }}
            >
              À propos du projet
            </Link>
            <span style={{ color: "var(--color-if-border-mid)" }}> · </span>
            <span className="text-xs flex items-center gap-1" style={{ color: "var(--color-if-text-xs)" }}>
              Fait avec <Heart size={10} style={{ color: "var(--color-if-accent)" }} fill="currentColor" /> par benjsant
            </span>
          </div>
        </div>
      </div>

      <div
        className="border-t px-4 py-3 text-center text-[11px]"
        style={{ borderColor: "var(--color-if-border)", color: "var(--color-if-text-xs)" }}
      >
        InfiniDex n&apos;est pas affilié à Nintendo, Game Freak ou The Pokémon Company.
        Pokémon Infinite Fusion est un fan-game non officiel.
      </div>
    </footer>
  );
}
