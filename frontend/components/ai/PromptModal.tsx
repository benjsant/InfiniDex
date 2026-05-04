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
      <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl bg-[rgb(14,14,22)] border border-[rgb(45,45,65)] shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[rgb(35,35,50)] shrink-0">
          <BookOpen size={16} className="text-indigo-400 shrink-0" />
          <p className="font-semibold text-[rgb(220,220,255)] flex-1">Prompt système envoyé au LLM</p>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[rgb(100,100,130)] hover:text-white hover:bg-[rgb(40,40,55)] transition-colors"
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-5 space-y-6">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-4 rounded bg-[rgb(25,25,38)] animate-pulse" style={{ width: `${60 + (i % 4) * 10}%` }} />
              ))}
            </div>
          ) : data ? (
            <>
              {/* System prompt */}
              <section>
                <h2 className="text-xs font-semibold text-[rgb(120,120,150)] uppercase tracking-wider mb-3">
                  System prompt
                </h2>
                <div className="rounded-xl bg-[rgb(10,10,18)] border border-[rgb(35,35,50)] p-4 prose prose-sm prose-invert max-w-none text-[rgb(180,180,200)] text-xs leading-relaxed">
                  <ReactMarkdown
                    components={{
                      h2:     ({ children }) => <h2 className="text-[rgb(200,200,240)] font-semibold mt-4 mb-1 first:mt-0">{children}</h2>,
                      p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul:     ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                      ol:     ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                      li:     ({ children }) => <li>{children}</li>,
                      strong: ({ children }) => <strong className="text-[rgb(220,220,255)] font-semibold">{children}</strong>,
                      code:   ({ children }) => <code className="bg-[rgb(20,20,35)] px-1 py-0.5 rounded text-indigo-300 font-mono">{children}</code>,
                    }}
                  >
                    {data.system_prompt}
                  </ReactMarkdown>
                </div>
              </section>

              {/* Tools */}
              <section>
                <h2 className="text-xs font-semibold text-[rgb(120,120,150)] uppercase tracking-wider mb-3">
                  {data.tools.length} outils disponibles
                </h2>
                <div className="space-y-2">
                  {data.tools.map((tool) => (
                    <div key={tool.name} className="flex gap-3 rounded-lg bg-[rgb(18,18,28)] border border-[rgb(35,35,50)] px-3 py-2.5">
                      <Cog size={13} className="text-indigo-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-mono text-indigo-300 font-semibold">{tool.name}</p>
                        <p className="text-[11px] text-[rgb(140,140,165)] leading-snug mt-0.5 line-clamp-2">{tool.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Context note */}
              <section className="flex gap-2 rounded-lg bg-amber-950/20 border border-amber-800/30 px-3 py-2.5 text-[11px] text-amber-300/80">
                <History size={13} className="shrink-0 mt-0.5" />
                <p>
                  Les {data.max_history_messages} derniers messages de la conversation sont ajoutés après le system prompt,
                  suivis des résultats des outils appelés à chaque tour.
                </p>
              </section>
            </>
          ) : (
            <p className="text-center text-[rgb(120,120,140)] py-8">Impossible de charger le prompt.</p>
          )}
        </div>
      </div>
    </div>
  );
}
