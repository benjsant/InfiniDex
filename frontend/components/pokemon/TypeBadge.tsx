import { typeColor, typeTextColor } from "@/lib/constants";

interface TypeBadgeProps {
  typeName: string;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export function TypeBadge({ typeName, label, size = "md", className }: TypeBadgeProps) {
  const bg    = typeColor(typeName);
  const color = typeTextColor(typeName);

  return (
    <span
      className={`inline-flex items-center justify-center rounded font-bold uppercase tracking-widest ${
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      } ${className ?? ""}`}
      style={{
        backgroundColor: bg,
        color,
        boxShadow: `0 0 8px ${bg}80, inset 0 1px 0 rgba(255,255,255,0.15)`,
        textShadow: "0 1px 2px rgba(0,0,0,0.4)",
      }}
    >
      {label ?? typeName}
    </span>
  );
}
