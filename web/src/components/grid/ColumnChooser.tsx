import type { VisibilityState } from "@tanstack/react-table";

const LABELS: Record<string, string> = {
  severity: "Severity",
  encoding: "Encoding",
  integrity: "Integrity",
  path: "Path",
  issueType: "Type",
};

export function ColumnChooser({
  testId = "grid-column-chooser",
  visibility,
  optionalKeys,
  onChange,
}: {
  testId?: string;
  visibility: VisibilityState;
  optionalKeys: readonly string[];
  onChange: (key: string, visible: boolean) => void;
}) {
  return (
    <details className="relative text-sm" data-testid={testId}>
      <summary className="cursor-pointer list-none rounded-md border border-outline px-3 py-1.5 text-on-surface-variant hover:bg-hover">
        열 선택
      </summary>
      <div className="absolute right-0 z-20 mt-1 min-w-[12rem] rounded-md border border-outline bg-surface-elevated p-2 shadow-lg">
        {optionalKeys.map((key) => (
          <label key={key} className="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              data-testid={`column-toggle-${key}`}
              checked={visibility[key] !== false}
              onChange={(e) => onChange(key, e.target.checked)}
            />
            <span>{LABELS[key] ?? key}</span>
          </label>
        ))}
      </div>
    </details>
  );
}
