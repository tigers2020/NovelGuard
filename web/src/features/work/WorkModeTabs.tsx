import type { WorkMode } from "../../types/snapshot";

const tabs: { id: WorkMode; label: string }[] = [
  { id: "scan", label: "스캔" },
  { id: "resolve", label: "검토 · 정리" },
  { id: "quality", label: "품질" },
  { id: "finalize", label: "적용 · 검증" },
];

export function WorkModeTabs({
  mode,
  onModeChange,
}: {
  mode: WorkMode;
  onModeChange: (mode: WorkMode) => void;
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-outline bg-background px-5 py-3">
      <div className="flex rounded-md border border-outline bg-surface p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            data-testid={`work-mode-tab-${tab.id}`}
            onClick={() => onModeChange(tab.id)}
            className={`rounded-sm px-4 py-2 text-sm font-semibold transition ${
              mode === tab.id
                ? "bg-primary text-background"
                : "text-on-surface-variant hover:bg-hover"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted">Mode-based Hybrid · no 4-card dashboard</p>
    </div>
  );
}
