// Next 16 a retiré `next lint` : ESLint tourne directement, en flat config.
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Règles React Compiler arrivées avec eslint-config-next 16. Elles visent
    // des motifs voulus ici (lecture de localStorage après hydratation pour
    // rester SSR-safe, ref d'AbortController) : signalées, pas bloquantes,
    // en attendant une réécriture dédiée.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
