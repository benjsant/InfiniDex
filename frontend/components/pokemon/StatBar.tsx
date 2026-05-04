import { statBarWidth, formatStatName } from "@/lib/utils";
import { STAT_LABELS } from "@/lib/constants";

interface StatBarProps {
  stat: string;
  value: number;
  max?: number;
  typeColor?: string;
}

export function StatBar({ stat, value, max = 255, typeColor }: StatBarProps) {
  const width = statBarWidth(value, max);
  const label = STAT_LABELS[stat] ?? stat;

  // Color: use type color if provided, else fallback to value-based color
  const barColor = typeColor
    ? typeColor
    : value >= 100 ? "#4ade80"
    : value >= 60  ? "#facc15"
    : "#f87171";

  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-right text-xs shrink-0" style={{ color: "var(--color-if-muted)" }}>
        {label}
      </span>
      <span className="w-8 text-right text-sm font-mono font-bold shrink-0" style={{ color: "var(--color-if-text)" }}>
        {value}
      </span>
      <div className="flex-1 h-2 rounded-full" style={{ background: "var(--color-if-border)" }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${width}%`,
            background: `linear-gradient(90deg, ${barColor}cc, ${barColor})`,
            boxShadow: `0 0 6px ${barColor}60`,
          }}
        />
      </div>
    </div>
  );
}
