"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, MapPin } from "lucide-react";
import { getAllTutors, getAllExpertMoves } from "@/lib/api";
import type { MoveTutorOut, MoveExpertOut } from "@/types/api";

function useTutors() {
  return useQuery({ queryKey: ["tutors-all"], queryFn: getAllTutors, staleTime: Infinity });
}

function useExpertMoves() {
  return useQuery({ queryKey: ["expert-moves-all"], queryFn: getAllExpertMoves, staleTime: Infinity });
}

function formatCurrency(t: MoveTutorOut): string {
  if (t.currency === "free") return "Gratuit";
  if (t.currency === "quest") return "Quête";
  return t.price != null ? `${t.price.toLocaleString("fr-FR")} P` : "—";
}

function groupByLocation(tutors: MoveTutorOut[]) {
  const map = new Map<string, { locationFr: string | null; tutors: MoveTutorOut[] }>();
  for (const t of tutors) {
    const key = t.location_name_en;
    if (!map.has(key)) map.set(key, { locationFr: t.location_name_fr, tutors: [] });
    map.get(key)!.tutors.push(t);
  }
  return Array.from(map.entries()).map(([nameEn, v]) => ({ nameEn, ...v }));
}

function groupExpertByLocation(experts: MoveExpertOut[]) {
  const map = new Map<string, MoveExpertOut[]>();
  for (const e of experts) {
    if (!map.has(e.location)) map.set(e.location, []);
    map.get(e.location)!.push(e);
  }
  return Array.from(map.entries());
}

const EXPERT_LOCATION_LABELS: Record<string, string> = {
  knot_island: "Île Nœud",
  boon_island: "Île Boon",
};

export default function TutorsPage() {
  const { data: tutors = [], isLoading: tutorsLoading, isError: tutorsError } = useTutors();
  const { data: experts = [], isLoading: expertsLoading, isError: expertsError } = useExpertMoves();

  const locationGroups = groupByLocation(tutors);
  const expertGroups = groupExpertByLocation(experts);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/moves"
          className="flex items-center gap-1 text-sm transition-colors"
          style={{ color: "var(--color-if-muted)" }}
        >
          <ArrowLeft size={14} />
          Capacités
        </Link>
        <span style={{ color: "var(--color-if-border-hi)" }}>/</span>
        <h1 className="text-xl sm:text-2xl font-bold" style={{ color: "var(--color-if-text)" }}>Maîtres des Capacités</h1>
      </div>

      {/* ── Classic tutors ─────────────────────────────────────────────── */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: "var(--color-if-text-dim)" }}>
          <MapPin size={16} style={{ color: "#e8b84b" }} />
          Tuteurs classiques
        </h2>

        {tutorsLoading ? (
          <SkeletonBlock rows={8} />
        ) : tutorsError ? (
          <p className="text-sm" style={{ color: "var(--color-if-muted)" }}>Impossible de charger les tuteurs.</p>
        ) : locationGroups.length === 0 ? (
          <p className="text-if-text-xs">Aucun tuteur trouvé.</p>
        ) : (
          <div className="space-y-4">
            {locationGroups.map(({ nameEn, locationFr, tutors: group }) => (
              <div key={nameEn} className="rounded-lg border border-if-input overflow-hidden">
                <div className="px-4 py-2 flex items-center gap-2" style={{ background: "var(--color-if-surface)" }}>
                  <MapPin size={13} style={{ color: "#e8b84b" }} className="shrink-0" />
                  <span className="font-semibold text-if-text-dim text-sm">
                    {locationFr ?? nameEn}
                  </span>
                  {locationFr && (
                    <span className="text-xs text-if-muted">({nameEn})</span>
                  )}
                </div>
                <table className="w-full text-sm">
                  <tbody>
                    {group.map((t) => (
                      <tr
                        key={t.id}
                        className="border-t border-if-input hover:bg-if-elevated transition-colors"
                      >
                        <td className="px-4 py-2.5 font-medium text-if-text-hi">
                          {t.move_name_fr ?? t.move_name_en}
                          {t.move_name_fr && (
                            <span className="ml-1 text-xs text-if-muted">
                              ({t.move_name_en})
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-[rgb(180,220,160)] whitespace-nowrap">
                          {formatCurrency(t)}
                        </td>
                        {t.npc_description && (
                          <td className="px-4 py-2.5 text-xs text-if-text-xs hidden sm:table-cell">
                            {t.npc_description}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Move Experts ──────────────────────────────────────────────── */}
      <section>
        <h2 className="text-lg font-semibold mb-1 flex items-center gap-2" style={{ color: "var(--color-if-text-dim)" }}>
          <MapPin size={16} style={{ color: "#e8b84b" }} />
          Experts en Capacités
        </h2>
        <p className="text-xs text-if-text-xs mb-4">
          Ces PNJ enseignent des capacités de fusion exclusives. Chaque expert demande de présenter
          des Pokémon ou types spécifiques pour débloquer la capacité.
        </p>

        {expertsLoading ? (
          <SkeletonBlock rows={6} />
        ) : expertsError ? (
          <p className="text-sm" style={{ color: "var(--color-if-muted)" }}>Impossible de charger les Move Experts.</p>
        ) : expertGroups.length === 0 ? (
          <p className="text-if-text-xs">Aucun expert trouvé.</p>
        ) : (
          <div className="space-y-4">
            {expertGroups.map(([location, moves]) => (
              <div key={location} className="rounded-lg border border-if-input overflow-hidden">
                <div className="px-4 py-2 flex items-center gap-2" style={{ background: "var(--color-if-surface)" }}>
                  <MapPin size={13} style={{ color: "#e8b84b" }} className="shrink-0" />
                  <span className="font-semibold text-if-text-dim text-sm">
                    {EXPERT_LOCATION_LABELS[location] ?? location}
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-if-card text-xs text-if-muted">
                      <th className="px-4 py-1.5 text-left font-medium">Capacité</th>
                      <th className="px-4 py-1.5 text-left font-medium">Pokémon requis</th>
                      <th className="px-4 py-1.5 text-left font-medium">Types requis</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moves.map((e) => (
                      <tr
                        key={e.move_id}
                        className="border-t border-if-input hover:bg-if-elevated transition-colors"
                      >
                        <td className="px-4 py-2.5 font-medium text-if-text-hi">
                          {e.move_name_fr ?? e.move_name_en}
                          {e.move_name_fr && (
                            <span className="ml-1 text-xs text-if-muted">
                              ({e.move_name_en})
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-[rgb(180,200,240)] text-xs">
                          {e.required_pokemon.length > 0
                            ? e.required_pokemon.join(", ")
                            : <span className="text-if-muted">—</span>}
                        </td>
                        <td className="px-4 py-2.5 text-[rgb(180,200,240)] text-xs">
                          {e.required_types.length > 0
                            ? e.required_types.join(", ")
                            : <span className="text-if-muted">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SkeletonBlock({ rows }: { rows: number }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-10 bg-if-elevated rounded" />
      ))}
    </div>
  );
}
