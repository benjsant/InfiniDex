/**
 * localStorage vu comme un store externe, pour `useSyncExternalStore`.
 *
 * - Côté serveur et pendant l'hydratation, React utilise le snapshot serveur
 *   (la valeur par défaut) : pas d'écart d'hydratation, pas de setState dans
 *   un effet au montage.
 * - Une écriture notifie tous les abonnés : deux composants qui lisent la
 *   même clé restent synchronisés, et l'évènement `storage` synchronise les
 *   autres onglets.
 * - Best-effort : si localStorage est indisponible ou plein (navigation
 *   privée, quota), la valeur vit en mémoire pour la session.
 */

const listeners = new Set<() => void>();
const memory = new Map<string, string>();

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

export function readRaw(key: string): string | null {
  if (memory.has(key)) return memory.get(key)!;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeRaw(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
    memory.delete(key);
  } catch {
    memory.set(key, value);
  }
  listeners.forEach((l) => l());
}
