"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AiChat } from "@/components/ai/AiChat";

function AiPageInner() {
  const searchParams = useSearchParams();
  const q   = searchParams.get("q")   ?? undefined;
  const ctx = searchParams.get("ctx") ?? undefined;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-[rgb(220,220,255)]">
          Assistant IA
        </h1>
        <p className="text-sm text-[rgb(120,120,140)]">
          Propulsé par DeepSeek · Spécialiste Pokémon Infinite Fusion
        </p>
      </div>
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
