type StatChipTone = "default" | "warn" | "danger" | "good";

const toneClasses: Record<StatChipTone, string> = {
  default: "border-outline bg-surface text-on-surface",
  warn: "border-secondary/30 bg-secondary/10 text-secondary",
  danger: "border-error/30 bg-error/10 text-error",
  good: "border-success/30 bg-success/10 text-success",
};

export function StatChip({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: StatChipTone;
}) {
  return (
    <div className={`rounded-md border px-3 py-2 ${toneClasses[tone]}`}>
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 text-sm font-semibold">{value}</div>
    </div>
  );
}
