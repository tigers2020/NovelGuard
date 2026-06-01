import type { VisibilityState } from "@tanstack/react-table";

const LABELS: Record<string, string> = {
  encoding: "Encoding",
  integrity: "Integrity",
  path: "Path",
  sizeBytes: "Size",
};

export function ColumnChooser({
  visibility,
  optionalKeys,
  onChange,
}: {
  visibility: VisibilityState;
  optionalKeys: readonly string[];
  onChange: (key: string, visible: boolean) => void;
}) {
  return (
    <details className="relative text-sm" data-testid="grid-column-chooser">
      <summary className="cursor-pointer list-none rounded-md border border-outline px-3 py-1.5 text-on-surface-variant hover:bg-hover [&::-webkit-details-marker]:hidden">
        열 선택
      </summary>
      <div className="absolute right-0 z-20 mt-1 min-w-[12rem] rounded-md border border-outline bg-surface-elevated p-2 shadow-lg">
        {optionalKeys.map((key) => (
          <label key={key} className="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              data-testid={`column-toggle-${key}`}
              checked={Boolean(visibility[key])}
              onChange={(e) => onChange(key, e.target.checked)}
            />
            <span>{LABELS[key] ?? key}</span>
          </label>
        ))}
      </div>
    </details>
  );
}
