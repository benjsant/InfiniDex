"use client";

import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { X, Cog, BookOpen, History } from "lucide-react";
import { getAiPrompt } from "@/lib/api";

export function PromptModal({ onClose }: { onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ai-prompt"],
    queryFn: getAiPrompt,
    staleTime: Infinity,
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl bg-if-deep border border-if-elevated shadow-2xl overflow-hidden">

        <div className="flex items-center gap-3 px-5 py-4 border-b border-if-input shrink-0">
          <BookOpen size={16} className="text-indigo-400 shrink-0" />
          <p className="font-semibold text-if-text-hi flex-1">Prompt système envoyé au LLM</p>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-if-muted hover:text-white hover:bg-if-input transition-colors"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-6">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-4 rounded bg-if-elevated animate-pulse" style={{ width: `${60 + (i % 4) * 10}%` }} />
              ))}
            </div>
          ) : data ? (
            <>
              <section>
                <h2 className="text-xs font-semibold text-if-text-xs uppercase tracking-wider mb-3">
                  System prompt
                </h2>
                <div className="rounded-xl bg-if-surface border border-if-input p-4 prose prose-sm prose-invert max-w-none text-if-text-lo text-xs leading-relaxed">
                  <ReactMarkdown
                    components={{
                      h2:     ({ children }) => <h2 className="text-if-text-dim font-semibold mt-4 mb-1 first:mt-0">{children}</h2>,
                      p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul:     ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                      ol:     ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                      li:     ({ children }) => <li>{children}</li>,
                      strong: ({ children }) => <strong className="text-if-text-hi font-semibold">{children}</strong>,
                      code:   ({ children }) => <code className="bg-if-card px-1 py-0.5 rounded text-indigo-300 font-mono">{children}</code>,
                    }}
                  >
                    {data.system_prompt}
                  </ReactMarkdown>
                </div>
              </section>

              <section>
                <h2 className="text-xs font-semibold text-if-text-xs uppercase tracking-wider mb-3">
                  {data.tools.length} outils disponibles
                </h2>
                <div className="space-y-2">
                  {data.tools.map((tool) => (
                    <div key={tool.name} className="flex gap-3 rounded-lg bg-if-card border border-if-input px-3 py-2.5">
                      <Cog size={13} className="text-indigo-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-mono text-indigo-300 font-semibold">{tool.name}</p>
                        <p className="text-[11px] text-if-text-xs leading-snug mt-0.5 line-clamp-2">{tool.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="flex gap-2 rounded-lg bg-amber-950/20 border border-amber-800/30 px-3 py-2.5 text-[11px] text-amber-300/80">
                <History size={13} className="shrink-0 mt-0.5" />
                <p>
                  Les {data.max_history_messages} derniers messages de la conversation sont ajoutés après le system prompt,
                  suivis des résultats des outils appelés à chaque tour.
                </p>
              </section>
            </>
          ) : (
            <p className="text-center text-if-text-xs py-8">Impossible de charger le prompt.</p>
          )}
        </div>
      </div>
    </div>
  );
}
