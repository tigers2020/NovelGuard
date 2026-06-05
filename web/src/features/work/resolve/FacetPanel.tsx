import type { ReviewViewMode } from "../../../types/review";

const viewModes: { id: ReviewViewMode; title: string; caption: string }[] = [
  { id: "action", title: "작업 대기열", caption: "검토 필요한 항목" },
  { id: "groups", title: "중복 그룹", caption: "그룹 중심" },
  { id: "move", title: "이동 계획", caption: "이동 예정" },
  { id: "all", title: "전체 파일", caption: "전체 파일" },
  { id: "conflicts", title: "충돌", caption: "충돌만" },
];

export function FacetPanel({
  viewMode,
  onViewModeChange,
  expanded,
  onExpandedChange,
}: {
  viewMode: ReviewViewMode;
  onViewModeChange: (mode: ReviewViewMode) => void;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
}) {
  const activeMode = viewModes.find((m) => m.id === viewMode) ?? viewModes[0];
  const panelState = expanded ? "expanded" : "collapsed";

  const toggleExpanded = () => {
    onExpandedChange(!expanded);
  };

  return (
    <aside
      className={`h-full min-h-0 shrink-0 overflow-y-auto border-r border-outline bg-background ${
        expanded ? "w-64 p-4" : "w-12 p-2"
      }`}
      data-testid="resolve-facet-panel"
      data-state={panelState}
    >
      <button
        type="button"
        className="w-full rounded-md px-1 py-1 text-left text-sm font-semibold text-on-surface hover:bg-hover"
        aria-expanded={expanded}
        onClick={toggleExpanded}
      >
        {expanded ? "▾" : "▸"} {expanded ? "검토 보기" : ""}
      </button>
      {!expanded && (
        <p
          className="mt-2 truncate text-[10px] font-semibold leading-tight text-muted"
          title={activeMode.title}
        >
          {activeMode.title}
        </p>
      )}
      {expanded && (
        <>
          <h2 className="sr-only">검토 보기</h2>
          <div className="mt-3 space-y-1">
            {viewModes.map((item) => (
              <button
                key={item.id}
                type="button"
                data-testid={`resolve-facet-${item.id}`}
                onClick={() => onViewModeChange(item.id)}
                className={`w-full rounded-md px-3 py-2 text-left transition ${
                  viewMode === item.id
                    ? "bg-primary text-background"
                    : "text-on-surface-variant hover:bg-hover"
                }`}
              >
                <div className="text-sm font-semibold">{item.title}</div>
                <div
                  className={`text-xs ${viewMode === item.id ? "opacity-80" : "text-muted"}`}
                >
                  {item.caption}
                </div>
              </button>
            ))}
          </div>
        </>
      )}
      {!expanded &&
        viewModes.map((item) => (
          <button
            key={item.id}
            type="button"
            hidden
            data-testid={`resolve-facet-${item.id}`}
            onClick={() => onViewModeChange(item.id)}
          />
        ))}
    </aside>
  );
}
