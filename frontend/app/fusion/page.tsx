"use client";

import { Suspense } from "react";
import { FusionSelector } from "@/components/fusion/FusionSelector";

export default function FusionPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2 text-[rgb(220,220,255)]">
        Calculateur de Fusion
      </h1>
      <p className="text-sm text-[rgb(120,120,140)] mb-8">
        Sélectionne la tête et le corps pour calculer les stats, types et voir le sprite de la fusion.
      </p>
      <Suspense>
        <FusionSelector />
      </Suspense>
    </div>
  );
}
