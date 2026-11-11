"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect, useCallback, useSyncExternalStore } from "react";
import { ToastProvider } from "@/components/layout/Toast";
import { readRaw, subscribe, writeRaw } from "@/lib/localStore";
import { ThemeContext } from "@/hooks/useTheme";
import type { Theme } from "@/hooks/useTheme";

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false;
  const e = error as { status?: number };
  // Retry 429 once after the Retry-After delay; retry other errors once too.
  return failureCount < 1 || e?.status !== 429;
}

function retryDelay(failureCount: number, error: unknown): number {
  const e = error as { retryAfter?: number };
  if (e?.retryAfter) return e.retryAfter * 1000;
  return Math.min(1000 * 2 ** failureCount, 30_000);
}

function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Valeur brute "dark" | "light" (format historique, pas de JSON).
  // "dark" côté serveur et pendant l'hydratation, puis la préférence stockée.
  const theme: Theme = useSyncExternalStore(
    subscribe,
    () => (readRaw("theme") === "light" ? "light" : "dark"),
    () => "dark",
  );

  // Synchronise <html> (système externe) avec le thème courant.
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme === "light" ? "light" : "");
  }, [theme]);

  const toggle = useCallback(() => {
    writeRaw("theme", readRaw("theme") === "light" ? "dark" : "light");
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            retry: shouldRetry,
            retryDelay,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
