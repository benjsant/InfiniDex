/**
 * Shared helpers for the OpenGraph image routes (`opengraph-image.tsx`).
 * Runs on the Next.js edge runtime — keep dependencies minimal.
 */

export const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;

export const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

function authHeaders(): Record<string, string> {
  return INTERNAL_API_KEY ? { "X-Internal-Key": INTERNAL_API_KEY } : {};
}

export async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, { headers: authHeaders() });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Satori fetches <img src> without our headers, so the key-protected sprite
// endpoint 403s. Pre-fetch it server-side with the key and inline as a data URL.
export async function fetchSpriteDataUrl(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return null;
    const bytes = new Uint8Array(await res.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return `data:image/png;base64,${btoa(binary)}`;
  } catch {
    return null;
  }
}
