"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AiChat } from "@/components/ai/AiChat";
import { getAiProvider } from "@/lib/api";

function AiPageInner() {
  const searchParams = useSearchParams();
  const q   = searchParams.get("q")   ?? undefined;
  const ctx = searchParams.get("ctx") ?? undefined;

  const { data: provider, isError: providerDown } = useQuery({
    queryKey: ["ai-provider"],
    queryFn: getAiProvider,
    staleTime: Infinity,
    retry: false,
  });

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-if-text-hi">
          Assistant IA
        </h1>
        <p className="text-sm text-if-text-xs">
          {provider
            ? `${provider.name} · ${provider.model} · Spécialiste Pokémon Infinite Fusion`
            : "Spécialiste Pokémon Infinite Fusion"}
        </p>
      </div>

      {providerDown && (
        <div className="mb-4 px-4 py-3 rounded-lg border border-amber-700/50 bg-amber-950/30 text-amber-300 text-sm">
          Aucun provider IA configuré — ajoute une clé <code className="font-mono text-xs bg-amber-900/40 px-1 py-0.5 rounded">DEEPSEEK_API_KEY</code> ou lance Ollama pour activer le chat.
        </div>
      )}

      <div className="flex-1 min-h-0">
        <AiChat initialMessage={q} initialContext={ctx} />
      </div>
    </div>
  );
}

export default function AiPage() {
  return (
    <Suspense>
      <AiPageInner />
    </Suspense>
  );
}
