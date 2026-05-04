import Image from "next/image";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { EvolutionOut } from "@/types/api";
import { basePokemonSprite } from "@/lib/constants";

interface EvolutionChainProps {
  pokemonId: number;
  evolutions: EvolutionOut[];
}

interface ChainNode {
  id: number;
  nationalId: number | null;
  nameFr: string | null;
  nameEn: string;
}

interface ChainEdge {
  from: number;
  to: number;
  condition: string;
  ifOverride: boolean;
}

function evolutionCondition(evo: EvolutionOut): string {
  const parts: string[] = [];
  if (evo.trigger_type === "level_up" && evo.min_level) {
    parts.push(`Niv. ${evo.min_level}`);
  } else if (evo.trigger_type === "use_item") {
    parts.push(evo.item_name_fr ?? evo.item_name_en ?? "Objet");
  } else if (evo.trigger_type === "trade") {
    parts.push("Échange");
  } else if (evo.trigger_type === "friendship") {
    parts.push("Amitié");
  } else {
    parts.push(evo.trigger_type);
  }
  if (evo.if_notes) parts.push(evo.if_notes);
  return parts.join(" · ");
}

function SpriteNode({ node, isCurrent }: { node: ChainNode; isCurrent: boolean }) {
  return (
    <Link
      href={`/pokedex/${node.id}`}
      className={`flex flex-col items-center gap-1.5 group ${
        isCurrent ? "opacity-100" : "opacity-70 hover:opacity-100 transition-opacity"
      }`}
      style={{ minWidth: "60px" }}
    >
      <div
        className="w-14 h-14 flex items-center justify-center rounded-xl transition-colors"
        style={{
          background: isCurrent ? "var(--color-if-surface)" : "var(--color-if-card)",
          border: `1px solid ${isCurrent ? "var(--color-if-accent)" : "var(--color-if-border)"}`,
        }}
      >
        <Image
          src={basePokemonSprite(node.nationalId ?? node.id)}
          alt={node.nameFr ?? node.nameEn}
          width={48}
          height={48}
          unoptimized
          className="object-contain"
          onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0.3"; }}
        />
      </div>
      <p className="text-xs font-medium text-center leading-tight" style={{ color: isCurrent ? "var(--color-if-accent)" : "var(--color-if-text-dim)" }}>
        {node.nameFr ?? node.nameEn}
      </p>
      <p className="text-[10px]" style={{ color: "var(--color-if-muted)" }}>#{node.id}</p>
    </Link>
  );
}

function Arrow({ condition, ifOverride }: { condition: string; ifOverride: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-1 shrink-0 max-w-[80px]">
      <span className="text-xs text-center leading-tight break-words" style={{ color: "var(--color-if-muted)" }}>
        {condition}
      </span>
      <ChevronRight size={16} style={{ color: "var(--color-if-border-hi)" }} />
      {ifOverride && (
        <span className="text-[10px] px-1 py-0.5 rounded" style={{ background: "rgba(232,184,75,0.12)", color: "var(--color-if-accent)" }}>IF</span>
      )}
    </div>
  );
}

export function EvolutionChain({ pokemonId, evolutions }: EvolutionChainProps) {
  if (evolutions.length === 0) {
    return (
      <p className="text-if-text-xs text-sm">
        Ce Pokémon n&apos;a pas d&apos;évolution dans Infinite Fusion.
      </p>
    );
  }

  // Build node map
  const nodeMap = new Map<number, ChainNode>();
  for (const evo of evolutions) {
    if (!nodeMap.has(evo.pokemon_id)) {
      nodeMap.set(evo.pokemon_id, {
        id: evo.pokemon_id,
        nationalId: evo.pokemon_national_id,
        nameFr: evo.pokemon_name_fr,
        nameEn: evo.pokemon_name_en ?? `#${evo.pokemon_id}`,
      });
    }
    if (!nodeMap.has(evo.evolves_into_id)) {
      nodeMap.set(evo.evolves_into_id, {
        id: evo.evolves_into_id,
        nationalId: evo.evolves_into_national_id,
        nameFr: evo.evolves_into_name_fr,
        nameEn: evo.evolves_into_name_en,
      });
    }
  }

  // Build edge list
  const edges: ChainEdge[] = evolutions.map((evo) => ({
    from: evo.pokemon_id,
    to: evo.evolves_into_id,
    condition: evolutionCondition(evo),
    ifOverride: evo.if_override,
  }));

  // Find root(s): IDs that are never a target
  const targetIds = new Set(edges.map((e) => e.to));
  const roots = [...nodeMap.keys()].filter((id) => !targetIds.has(id));

  // Build chains from each root (handles branches like Eevee)
  function buildChain(startId: number): number[][] {
    const outEdges = edges.filter((e) => e.from === startId);
    if (outEdges.length === 0) return [[startId]];
    const chains: number[][] = [];
    for (const edge of outEdges) {
      for (const tail of buildChain(edge.to)) {
        chains.push([startId, ...tail]);
      }
    }
    return chains;
  }

  const chains: number[][] = roots.flatMap((r) => buildChain(r));

  return (
    <div className="space-y-6">
      {chains.map((chain, ci) => (
        <div key={ci} className="flex items-center gap-1 flex-wrap">
          {chain.map((nodeId, i) => {
            const node = nodeMap.get(nodeId)!;
            const edge = i < chain.length - 1
              ? edges.find((e) => e.from === nodeId && e.to === chain[i + 1])
              : null;
            return (
              <div key={nodeId} className="flex items-center gap-1">
                <SpriteNode node={node} isCurrent={nodeId === pokemonId} />
                {edge && <Arrow condition={edge.condition} ifOverride={edge.ifOverride} />}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
