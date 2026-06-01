import type { ReviewViewMode } from "../../../types/review";

const viewModes: { id: ReviewViewMode; title: string; caption: string }[] = [
  { id: "action", title: "Action Queue", caption: "검토 필요한 항목" },
  { id: "groups", title: "Duplicate Groups", caption: "그룹 중심" },
  { id: "move", title: "Move Plan", caption: "이동 예정" },
  { id: "all", title: "All Files", caption: "전체 파일" },
  { id: "conflicts", title: "Conflicts", caption: "충돌만" },
];

export function FacetPanel({
  viewMode,
  onViewModeChange,
}: {
  viewMode: ReviewViewMode;
  onViewModeChange: (mode: ReviewViewMode) => void;
}) {
  return (
    <aside className="w-64 shrink-0 overflow-y-auto border-r border-outline bg-background p-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted">Review views</h2>
      <div className="mt-3 space-y-1">
        {viewModes.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onViewModeChange(item.id)}
            className={`w-full rounded-md px-3 py-2 text-left transition ${
              viewMode === item.id
                ? "bg-primary text-background"
                : "text-on-surface-variant hover:bg-hover"
            }`}
          >
            <div className="text-sm font-semibold">{item.title}</div>
            <div className={`text-xs ${viewMode === item.id ? "opacity-80" : "text-muted"}`}>
              {item.caption}
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}
