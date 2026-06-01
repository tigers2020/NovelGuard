import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { ReviewRow } from "../../../types/review";
import { proposedActionLabel, reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";

export function VirtualizedReviewGrid({
  rows,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
}: {
  rows: ReviewRow[];
  selectedRowId: string | null;
  onSelectRow: (row: ReviewRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
}) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 8,
  });

  const handleScroll = () => {
    const el = parentRef.current;
    if (!el || !onNearEnd) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 120) {
      onNearEnd();
    }
  };

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col border-r border-outline bg-background">
      <div className="grid grid-cols-[5rem_5rem_minmax(12rem,1fr)_8rem_8rem_5rem] border-b border-outline bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
        <div>Status</div>
        <div>Type</div>
        <div>Name / Keeper</div>
        <div>Action</div>
        <div>Target</div>
        <div>Conf.</div>
      </div>
      <div
        ref={parentRef}
        className="min-h-0 flex-1 overflow-auto"
        onScroll={handleScroll}
      >
        <div
          className="relative w-full"
          style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            const selected = selectedRowId === row.id;
            return (
              <button
                key={row.id}
                type="button"
                onClick={() => onSelectRow(row)}
                className={`absolute left-0 grid w-full grid-cols-[5rem_5rem_minmax(12rem,1fr)_8rem_8rem_5rem] items-center border-b border-outline px-3 text-left text-sm transition ${
                  selected
                    ? "bg-primary/15 outline outline-1 outline-primary/40"
                    : "bg-background hover:bg-hover"
                }`}
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <span
                  className={
                    row.status === "conflict"
                      ? "font-semibold text-error"
                      : row.status === "approved"
                        ? "font-semibold text-success"
                        : "text-on-surface-variant"
                  }
                >
                  {reviewStatusLabel[row.status]}
                </span>
                <span className="text-muted">{reviewTypeLabel[row.type]}</span>
                <span className="min-w-0">
                  <span className="block truncate font-medium text-on-surface">{row.name}</span>
                  <span className="block truncate text-xs text-muted">
                    keeper: {row.keeperLabel}
                  </span>
                </span>
                <span className="truncate text-on-surface-variant">
                  {proposedActionLabel[row.proposedAction]}
                </span>
                <span className="truncate text-muted">{row.targetFolder}</span>
                <span className="tabular-nums text-on-surface-variant">
                  {row.confidence ?? "—"}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-outline bg-surface px-4 py-2 text-xs text-muted">
        <span>
          VirtualizedReviewGrid · {rowVirtualizer.getVirtualItems().length} visible
          {loadingMore ? " · loading…" : ""}
        </span>
        <span>{rows.length.toLocaleString()} loaded rows</span>
      </div>
    </section>
  );
}
