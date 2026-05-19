import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
      <p className="text-8xl font-bold mb-4" style={{ color: "var(--color-if-border)" }}>404</p>
      <h1 className="text-2xl font-bold text-if-text-hi mb-2">Page introuvable</h1>
      <p className="text-sm text-if-text-xs mb-8 max-w-sm">
        Cette fusion n&apos;existe pas encore — ou elle a été renvoyée dans la Box PC.
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link
          href="/fusion"
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          Calculateur de fusion
        </Link>
        <Link
          href="/pokedex"
          className="px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          style={{ background: "var(--color-if-card)", border: "1px solid var(--color-if-border)", color: "var(--color-if-muted)" }}
        >
          Pokédex
        </Link>
      </div>
    </div>
  );
}
