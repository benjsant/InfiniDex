/**
 * Marks a Pokémon that only exists in Pokémon Infinite Fusion 2 (Hoenn).
 *
 * The DB flag is still named `is_hoenn_only`; the user-facing wording is the
 * game's name, which is what players actually search for.
 */
export function GameBadge({ isHoennOnly, size = "sm" }: { isHoennOnly: boolean; size?: "sm" | "md" }) {
  if (!isHoennOnly) return null;
  const cls = size === "md" ? "text-[11px] px-2 py-0.5" : "text-[9px] px-1.5 py-px";
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold tracking-wide ${cls}`}
      style={{ background: "rgba(232,184,75,0.15)", color: "#e8b84b", border: "1px solid rgba(232,184,75,0.4)" }}
      title="Disponible uniquement dans Pokémon Infinite Fusion 2 (Hoenn)"
    >
      IF2
    </span>
  );
}
