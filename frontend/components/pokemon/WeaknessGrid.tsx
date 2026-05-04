import type { WeaknessOut } from "@/types/api";
import { multiplierLabel, multiplierColor } from "@/lib/utils";

interface WeaknessGridProps {
  weaknesses: WeaknessOut[];
}

export function WeaknessGrid({ weaknesses }: WeaknessGridProps) {
  // Only show non-neutral (multiplier != 1)
  const relevant = weaknesses.filter((w) => w.multiplier !== 1);

  const immune    = relevant.filter((w) => w.multiplier === 0);
  const resistant = relevant.filter((w) => w.multiplier < 1 && w.multiplier > 0);
  const weak      = relevant.filter((w) => w.multiplier > 1);

  return (
    <div className="space-y-4">
      {immune.length > 0 && (
        <Section label="Immunité (×0)" items={immune} />
      )}
      {resistant.length > 0 && (
        <Section label="Résistances" items={resistant} />
      )}
      {weak.length > 0 && (
        <Section label="Faiblesses" items={weak} />
      )}
      {relevant.length === 0 && (
        <p className="text-if-text-xs text-sm">
          Aucune faiblesse ou résistance particulière.
        </p>
      )}
    </div>
  );
}

function Section({
  label,
  items,
}: {
  label: string;
  items: WeaknessOut[];
}) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-if-text-xs uppercase tracking-wider mb-2">
        {label}
      </h4>
      <div className="flex flex-wrap gap-2">
        {items.map((w) => (
          <div key={w.attacking_type_id} className="flex items-center gap-1">
            <span className="text-xs text-if-text-dim">
              {w.attacking_type_name_fr ?? w.attacking_type_name_en}
            </span>
            <span
              className={`text-xs font-bold px-1.5 py-0.5 rounded ${multiplierColor(w.multiplier)}`}
            >
              {multiplierLabel(w.multiplier)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
