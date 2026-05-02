"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAbilities, getAbility } from "@/lib/api";
import { SearchBar } from "@/components/layout/SearchBar";
import { normalize } from "@/lib/utils";
import type { AbilityDetail } from "@/types/api";

export default function AbilitiesPage() {
  const { data: abilities = [], isLoading } = useQuery({
    queryKey: ["abilities"],
    queryFn: getAbilities,
  });

  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: detail } = useQuery({
    queryKey: ["ability", selectedId],
    queryFn: () => getAbility(selectedId!),
    enabled: selectedId != null,
  });

  const filtered = useMemo(() => {
    if (q.trim().length < 2) return abilities;
    const nq = normalize(q);
    return abilities.filter(
      (a) =>
        normalize(a.name_en).includes(nq) ||
        (a.name_fr && normalize(a.name_fr).includes(nq)),
    );
  }, [abilities, q]);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-6" style={{ color: "#e1e4ff" }}>Talents</h1>

      <SearchBar
        onSearch={setQ}
        placeholder="Rechercher un talent…"
        className="mb-4"
      />

      <p className="text-sm text-[rgb(120,120,140)] mb-3">{filtered.length} talents</p>

      <div className="flex flex-col md:flex-row gap-4">
        {/* List */}
        <div className="flex-1 overflow-y-auto max-h-[60vh] md:max-h-[70vh] rounded-lg border border-[#1e2240]">
          {isLoading ? (
            <div className="animate-pulse p-4 space-y-2">
              {Array.from({ length: 15 }).map((_, i) => (
                <div key={i} className="h-10 bg-[#1e2240] rounded" />
              ))}
            </div>
          ) : (
            filtered.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedId(selectedId === a.id ? null : a.id)}
                className="w-full flex items-center justify-between px-4 py-3 border-b border-[#1a1d35] hover:bg-[#1e2240] transition-colors text-left"
                style={selectedId === a.id ? { borderLeft: "2px solid #e8b84b", background: "#16192e" } : undefined}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: "#e1e4ff" }}>
                    {a.name_fr ?? a.name_en}
                  </p>
                  {a.name_fr && (
                    <p className="text-xs" style={{ color: "#6b7199" }}>{a.name_en}</p>
                  )}
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detail panel */}
        {detail && (
          <div className="w-full md:w-72 shrink-0 rounded-lg p-4 h-fit md:sticky top-20" style={{ background: "#111428", border: "1px solid #1e2240" }}>
            <h2 className="font-bold mb-0.5" style={{ color: "#e1e4ff" }}>{detail.name_fr ?? detail.name_en}</h2>
            {detail.name_fr && (
              <p className="text-xs mb-3" style={{ color: "#6b7199" }}>{detail.name_en}</p>
            )}
            {detail.description_fr && (
              <p className="text-sm mb-2" style={{ color: "#c8cbf0" }}>{detail.description_fr}</p>
            )}
            {detail.description_en && (
              <p className="text-sm pt-2 mt-2" style={{ color: "#6b7199", borderTop: "1px solid #1e2240" }}>
                {detail.description_en}
              </p>
            )}
            {detail.if_modified && (
              <div className="mt-3 px-2 py-1.5 rounded" style={{ background: "rgba(232,184,75,0.08)", border: "1px solid rgba(232,184,75,0.25)" }}>
                <p className="text-xs font-semibold" style={{ color: "#e8b84b" }}>Modifié dans IF</p>
                {detail.if_notes && (
                  <p className="text-xs mt-0.5" style={{ color: "#c8a84b" }}>{detail.if_notes}</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
