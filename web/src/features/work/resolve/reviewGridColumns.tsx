import { createColumnHelper } from "@tanstack/react-table";
import type { ReviewRow } from "../../../types/review";
import { proposedActionLabel, reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";

const helper = createColumnHelper<ReviewRow>();

export const REVIEW_GRID_SIZING_KEY = "novelguard.reviewGrid.sizing.v1";

/** TanStack table state: all columns enabled; render uses width-based merge. */
export const reviewGridAllColumnsVisible: Record<string, boolean> = {
  batchSelect: true,
  status: true,
  type: true,
  name: true,
  proposedAction: true,
  targetFolder: true,
  confidence: true,
  encoding: true,
  integrity: true,
  path: true,
  sizeBytes: true,
};

import type { ColumnDef } from "@tanstack/react-table";

export function buildReviewGridColumns(options?: {
  explicitRowIds: ReadonlySet<string>;
  onToggleExplicit: (row: ReviewRow) => void;
  allVisibleSelected?: boolean;
  someVisibleSelected?: boolean;
  onToggleSelectAllVisible?: () => void;
}): ColumnDef<ReviewRow>[] {
  const batchColumn: ColumnDef<ReviewRow>[] = options
    ? [
        helper.display({
          id: "batchSelect",
          header: () => (
            <input
              type="checkbox"
              aria-label="전체 선택"
              title="현재 로드된 행 전체 선택"
              data-testid="resolve-select-all-visible"
              checked={Boolean(options.allVisibleSelected)}
              ref={(el) => {
                if (el) {
                  el.indeterminate = Boolean(
                    options.someVisibleSelected && !options.allVisibleSelected,
                  );
                }
              }}
              onChange={(event) => {
                event.stopPropagation();
                options.onToggleSelectAllVisible?.();
              }}
              onClick={(event) => event.stopPropagation()}
            />
          ),
          enableSorting: false,
          meta: { gridWidth: "2.5rem", minWidthPx: 40, resizable: false },
          cell: ({ row }) => (
            <input
              type="checkbox"
              aria-label={`Select ${row.original.name} for batch actions`}
              data-testid={`resolve-row-check-${row.original.id}`}
              checked={options.explicitRowIds.has(row.original.id)}
              onChange={(event) => {
                event.stopPropagation();
                options.onToggleExplicit(row.original);
              }}
              onClick={(event) => event.stopPropagation()}
            />
          ),
        }),
      ]
    : [];

  return [
    ...batchColumn,
    helper.accessor("status", {
      header: "Status",
      enableSorting: true,
      meta: { gridWidth: "5rem", minWidthPx: 56, resizable: true },
      cell: (ctx) => (
        <span
          className={
            ctx.getValue() === "conflict"
              ? "font-semibold text-error"
              : ctx.getValue() === "approved"
                ? "font-semibold text-success"
                : "text-on-surface-variant"
          }
        >
          {reviewStatusLabel[ctx.getValue()]}
        </span>
      ),
    }),
    helper.accessor("type", {
      header: "Type",
      enableSorting: true,
      meta: { gridWidth: "5rem", minWidthPx: 56, resizable: true },
      cell: (ctx) => {
        const value = ctx.getValue();
        const isNear = value === "near";
        const isRelation = value === "relation";
        return (
          <span
            className={
              isNear || isRelation ? "font-semibold text-secondary" : "text-muted"
            }
          >
            {isNear ? "Near" : isRelation ? "Relation" : reviewTypeLabel[value]}
          </span>
        );
      },
    }),
    helper.accessor("name", {
      id: "name",
      header: "Name / Keeper",
      enableSorting: true,
      meta: { gridWidth: "minmax(0,1fr)", minWidthPx: 160, resizable: true },
      cell: (ctx) => {
        const row = ctx.row.original;
        return (
          <>
            <span className="block truncate font-medium text-on-surface">{row.name}</span>
            <span className="block truncate text-xs text-muted">keeper: {row.keeperLabel}</span>
          </>
        );
      },
    }),
    helper.accessor("proposedAction", {
      header: "Action",
      enableSorting: true,
      meta: { gridWidth: "7rem", minWidthPx: 72, resizable: true },
      cell: (ctx) => (
        <span className="truncate text-on-surface-variant">
          {proposedActionLabel[ctx.getValue()]}
        </span>
      ),
    }),
    helper.accessor("targetFolder", {
      header: "Target",
      enableSorting: true,
      meta: { gridWidth: "7rem", minWidthPx: 72, resizable: true },
      cell: (ctx) => <span className="truncate text-muted">{ctx.getValue() ?? "—"}</span>,
    }),
    helper.accessor("confidence", {
      header: "Conf.",
      enableSorting: true,
      meta: { gridWidth: "4.5rem", minWidthPx: 52, resizable: true },
      cell: (ctx) => (
        <span className="tabular-nums text-on-surface-variant">{ctx.getValue() ?? "—"}</span>
      ),
    }),
    helper.accessor("encoding", {
      header: "Encoding",
      enableSorting: true,
      meta: { gridWidth: "6rem", minWidthPx: 64, resizable: true },
      cell: (ctx) => <span className="text-secondary">{ctx.getValue() ?? "—"}</span>,
    }),
    helper.accessor("integrity", {
      header: "Integrity",
      enableSorting: true,
      meta: { gridWidth: "8rem", minWidthPx: 72, resizable: true },
      cell: (ctx) => <span className="text-muted">{ctx.getValue() ?? "—"}</span>,
    }),
    helper.accessor((row) => row.path ?? "—", {
      id: "path",
      header: "Path",
      enableSorting: false,
      meta: { gridWidth: "minmax(0,1.2fr)", minWidthPx: 120, resizable: true },
      cell: (ctx) => <span className="truncate text-xs text-muted">{String(ctx.getValue())}</span>,
    }),
    helper.accessor("sizeBytes", {
      header: "Size",
      enableSorting: true,
      meta: { gridWidth: "5rem", minWidthPx: 56, resizable: true },
      cell: (ctx) => {
        const v = ctx.getValue();
        return (
          <span className="tabular-nums text-on-surface-variant">
            {v ? `${(v / (1024 * 1024)).toFixed(1)} MB` : "—"}
          </span>
        );
      },
    }),
  ] as ColumnDef<ReviewRow>[];
}
