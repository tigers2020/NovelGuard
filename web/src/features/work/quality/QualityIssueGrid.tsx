import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { QualityRow } from "../../../types/quality";

export function QualityIssueGrid({
  rows,
  selectedId,
  onSelect,
}: {
  rows: QualityRow[];
  selectedId: string | null;
  onSelect: (row: QualityRow) => void;
}) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 6,
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-md border border-outline bg-background">
      <div className="grid grid-cols-[1fr_6rem_8rem] border-b border-outline bg-surface px-3 py-2 text-xs font-semibold uppercase text-muted">
        <div>Name</div>
        <div>Encoding</div>
        <div>Integrity</div>
      </div>
      <div ref={parentRef} className="min-h-0 flex-1 overflow-auto">
        <div className="relative w-full" style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            const selected = row.id === selectedId;
            return (
              <button
                key={row.id}
                type="button"
                onClick={() => onSelect(row)}
                className={`absolute left-0 grid w-full grid-cols-[1fr_6rem_8rem] items-center border-b border-outline px-3 py-2 text-left text-sm ${
                  selected ? "bg-primary/15" : "hover:bg-hover"
                }`}
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <span className="truncate font-medium text-on-surface">{row.name}</span>
                <span className="text-secondary">{row.encoding}</span>
                <span className={row.severity === "error" ? "text-error" : "text-muted"}>
                  {row.integrity}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
