import { ExternalLink, Database, Brain, Layers, GitMerge, Code2, Heart } from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "À propos — InfiniDex",
  description: "Présentation du projet InfiniDex : stack technique, sources de données, remerciements.",
};

const SOURCES = [
  {
    name: "Pokémon Infinite Fusion",
    url: "https://infinitefusion.fandom.com/wiki/Pok%C3%A9mon_Infinite_Fusion_Wiki",
    desc: "Wiki officiel du jeu — liste des Pokémon, mouvements, capacités, lieux d'apparition, tuteurs, Move Experts, objets.",
  },
  {
    name: "PokeAPI",
    url: "https://pokeapi.co",
    desc: "Stats de base, noms en français, chaînes d'évolution, capacités apprenables, descriptions de talents.",
  },
  {
    name: "Pokepedia",
    url: "https://www.pokepedia.fr",
    desc: "Mapping des noms français pour les Pokémon du jeu de base.",
  },
  {
    name: "infinitefusion.net",
    url: "https://www.infinitefusion.net",
    desc: "Spritesheets officiels des fusions (168 000+ sprites extraits et servis localement).",
  },
  {
    name: "Sprite Pack communautaire",
    url: "https://discord.gg/infinitefusion",
    desc: "7 000+ créateurs de sprites custom qui enrichissent le jeu chaque mois.",
  },
];

const STACK = [
  { label: "Backend", value: "FastAPI · Python 3.12 · PostgreSQL 16 · SQLAlchemy · uv" },
  { label: "Frontend", value: "Next.js 15 · React 19 · TypeScript · Tailwind CSS 4" },
  { label: "ETL", value: "Pipeline Python en 14 étapes · Scrapy · PokeAPI · MediaWiki API" },
  { label: "IA", value: "DeepSeek API · fallback OpenRouter · fallback Ollama local · Tool calling natif · Cascade DB → Wiki → Web" },
  { label: "Infra", value: "Docker Compose · Nginx (sprites CDN) · Prefect (scheduler)" },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-12">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-3" style={{ color: "var(--color-if-text-hi)" }}>
          À propos de InfiniDex
        </h1>
        <p className="text-base leading-relaxed" style={{ color: "var(--color-if-text-dim)" }}>
          InfiniDex est un Pokédex open source dédié à{" "}
          <a
            href="https://infinitefusion.fandom.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:opacity-80"
            style={{ color: "var(--color-if-accent)" }}
          >
            Pokémon Infinite Fusion
          </a>
          , un fan-game qui permet de fusionner n&apos;importe quels deux Pokémon. Il centralise
          toutes les données du jeu (Pokédex, fusions, mouvements, lieux, objets, types) et les
          enrichit avec un assistant IA agentique capable d&apos;interroger la base de données, le wiki
          officiel et le web.
        </p>
      </div>

      {/* Ce que fait l'app */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-hi)" }}>
          <GitMerge size={18} style={{ color: "var(--color-if-accent)" }} />
          Fonctionnalités
        </h2>
        <ul className="space-y-2 text-sm" style={{ color: "var(--color-if-text-dim)" }}>
          {[
            "Pokédex complet des 572 Pokémon d'Infinite Fusion (Kanto + Hoenn)",
            "Calculateur de fusion avec stats, types, mouvements et sprites",
            "168 000+ sprites de fusion servis localement via CDN",
            "Données complètes : mouvements, tuteurs, Move Experts, CTs, objets, types, lieux",
            "23 triples fusions officielles",
            "Page créateurs avec 7 000+ artistes de sprites",
            "Assistant IA agentique avec tool calling sur la BDD, le wiki IF et le web (DeepSeek API · OpenRouter · Ollama)",
            "Mode clair / sombre, responsive mobile",
          ].map((f) => (
            <li key={f} className="flex items-start gap-2">
              <span style={{ color: "var(--color-if-accent)" }}>·</span>
              {f}
            </li>
          ))}
        </ul>
      </section>

      {/* Stack */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-hi)" }}>
          <Code2 size={18} style={{ color: "var(--color-if-accent)" }} />
          Stack technique
        </h2>
        <div className="space-y-2">
          {STACK.map((s) => (
            <div key={s.label} className="flex gap-3 text-sm">
              <span className="w-20 shrink-0 font-medium" style={{ color: "var(--color-if-muted)" }}>{s.label}</span>
              <span style={{ color: "var(--color-if-text-dim)" }}>{s.value}</span>
            </div>
          ))}
        </div>
      </section>

      {/* IA */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-hi)" }}>
          <Brain size={18} style={{ color: "var(--color-if-accent)" }} />
          Assistant IA
        </h2>
        <p className="text-sm leading-relaxed" style={{ color: "var(--color-if-text-dim)" }}>
          L&apos;assistant utilise un système de{" "}
          <strong style={{ color: "var(--color-if-text)" }}>tool calling agentique</strong> : à chaque
          question, le modèle choisit quels outils appeler (base de données interne, wiki IF, recherche web)
          avant de formuler une réponse. Si aucune source ne remonte d&apos;information pertinente, l&apos;assistant
          répond explicitement qu&apos;il ne sait pas — jamais d&apos;invention. Les outils appelés et les sources
          utilisées sont affichés en temps réel dans l&apos;interface.
        </p>
        <Link
          href="/ai"
          className="inline-flex items-center gap-1.5 mt-3 text-sm font-medium hover:opacity-80"
          style={{ color: "var(--color-if-accent)" }}
        >
          Essayer l&apos;assistant →
        </Link>
      </section>

      {/* Sources */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-hi)" }}>
          <Database size={18} style={{ color: "var(--color-if-accent)" }} />
          Sources de données
        </h2>
        <div className="space-y-4">
          {SOURCES.map((s) => (
            <div key={s.name} className="flex gap-3">
              <ExternalLink size={14} className="mt-0.5 shrink-0" style={{ color: "var(--color-if-muted)" }} />
              <div>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium hover:opacity-80"
                  style={{ color: "var(--color-if-text)" }}
                >
                  {s.name}
                </a>
                <p className="text-xs mt-0.5" style={{ color: "var(--color-if-text-lo)" }}>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Remerciements */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-hi)" }}>
          <Heart size={18} style={{ color: "var(--color-if-accent)" }} fill="currentColor" />
          Remerciements
        </h2>
        <div className="text-sm leading-relaxed space-y-3" style={{ color: "var(--color-if-text-dim)" }}>
          <p>
            Un immense merci à{" "}
            <strong style={{ color: "var(--color-if-text)" }}>Schrroms</strong> et toute l&apos;équipe
            de développement de{" "}
            <a
              href="https://infinitefusion.fandom.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:opacity-80"
              style={{ color: "var(--color-if-accent)" }}
            >
              Pokémon Infinite Fusion
            </a>{" "}
            pour ce fan-game extraordinaire qui a inspiré ce projet.
          </p>
          <p>
            Merci à la communauté des{" "}
            <Link href="/creators" className="underline underline-offset-2 hover:opacity-80" style={{ color: "var(--color-if-accent)" }}>
              7 000+ créateurs de sprites
            </Link>{" "}
            qui contribuent chaque mois au Sprite Pack et donnent vie aux fusions.
          </p>
          <p>
            Merci aux équipes de{" "}
            <a href="https://pokeapi.co" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:opacity-80" style={{ color: "var(--color-if-accent)" }}>PokeAPI</a>
            {" "}et{" "}
            <a href="https://www.pokepedia.fr" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:opacity-80" style={{ color: "var(--color-if-accent)" }}>Pokepedia</a>
            {" "}pour leurs APIs publiques et leur travail de documentation.
          </p>
          <p className="text-xs pt-2" style={{ color: "var(--color-if-text-xs)" }}>
            InfiniDex est un projet fan non officiel, sans affiliation avec Nintendo, Game Freak
            ou The Pokémon Company. Pokémon est une marque déposée de Nintendo / Game Freak.
          </p>
        </div>
      </section>
    </div>
  );
}
