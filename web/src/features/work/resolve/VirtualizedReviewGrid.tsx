import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { ReviewRow } from "../../../types/review";
import { proposedActionLabel, reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";
import { gridTemplateForColumns, useReviewGridColumns } from "./useReviewGridColumns";

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
  const sectionRef = useRef<HTMLElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);
  const columns = useReviewGridColumns(sectionRef);
  const gridStyle = { gridTemplateColumns: gridTemplateForColumns(columns) };

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
    <section
      ref={sectionRef}
      className="flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden border-r border-outline bg-background"
    >
      <div
        className="grid border-b border-outline bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
        style={gridStyle}
      >
        {columns.status && <div>Status</div>}
        {columns.type && <div>Type</div>}
        <div>Name / Keeper</div>
        {columns.action && <div>Action</div>}
        {columns.target && <div>Target</div>}
        {columns.conf && <div>Conf.</div>}
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
                className={`absolute left-0 grid w-full items-center border-b border-outline px-3 text-left text-sm transition ${
                  selected
                    ? "bg-primary/15 outline outline-1 outline-primary/40"
                    : "bg-background hover:bg-hover"
                }`}
                style={{
                  ...gridStyle,
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {columns.status && (
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
                )}
                {columns.type && (
                  <span className="text-muted">{reviewTypeLabel[row.type]}</span>
                )}
                <span className="min-w-0">
                  <span className="block truncate font-medium text-on-surface">{row.name}</span>
                  <span className="block truncate text-xs text-muted">
                    keeper: {row.keeperLabel}
                  </span>
                </span>
                {columns.action && (
                  <span className="truncate text-on-surface-variant">
                    {proposedActionLabel[row.proposedAction]}
                  </span>
                )}
                {columns.target && (
                  <span className="truncate text-muted">{row.targetFolder}</span>
                )}
                {columns.conf && (
                  <span className="tabular-nums text-on-surface-variant">
                    {row.confidence ?? "—"}
                  </span>
                )}
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
