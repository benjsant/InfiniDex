import { NextRequest, NextResponse } from "next/server";

// Proxy catch-all : toutes les requêtes `/api/*` sont forwardées au backend
// via le réseau Docker interne. Le browser ne voit JAMAIS l'URL réelle du
// backend. Env lue à runtime (pas de rebuild nécessaire pour changer la cible).
// In Docker: BACKEND_INTERNAL_URL=http://backend:8000 (set by docker-compose).
// In host dev mode: falls back to localhost:FUSIONDEX_BACKEND_PORT (from .env).
const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ||
  `http://localhost:${process.env.FUSIONDEX_BACKEND_PORT ?? "58000"}`;

// Shared secret between Next.js and FastAPI — never sent to the browser.
// If not set, the backend runs without key enforcement (dev mode).
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, path: string[]) {
  const target = `${BACKEND_URL}/${path.join("/")}${req.nextUrl.search}`;

  // Retire les headers qui concernent le hop client→Next et pourraient gêner
  // la requête server-to-server (hop-by-hop + host).
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  // Inject the internal key — server-side only, never exposed to the browser.
  if (INTERNAL_API_KEY) headers.set("X-Internal-Key", INTERNAL_API_KEY);

  const isReadOnly = ["GET", "HEAD"].includes(req.method);
  const init: RequestInit = {
    method: req.method,
    headers,
    body: isReadOnly ? undefined : await req.arrayBuffer(),
    // Follow redirects server-side so the browser never sees internal Docker
    // URLs (e.g. Location: http://backend:8000/...) from FastAPI slash-redirects.
    redirect: "follow",
    // Let GET/HEAD responses be cached by Next.js according to the upstream
    // Cache-Control headers. Force no-store only for mutating requests.
    ...(isReadOnly ? {} : { cache: "no-store" }),
  };

  try {
    const upstream = await fetch(target, init);
    // On stream la réponse telle quelle (status, headers, body).
    const resHeaders = new Headers(upstream.headers);
    // Drop les headers hop-by-hop côté réponse aussi.
    ["transfer-encoding", "connection"].forEach((h) => resHeaders.delete(h));
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: resHeaders,
    });
  } catch (err) {
    return NextResponse.json(
      { detail: `Backend proxy error: ${(err as Error).message}` },
      { status: 502 },
    );
  }
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function OPTIONS(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
