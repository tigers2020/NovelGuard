import { createColumnHelper } from "@tanstack/react-table";
import type { ReviewRow } from "../../../types/review";
import { proposedActionLabel, reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";

const helper = createColumnHelper<ReviewRow>();

export const REVIEW_GRID_SIZING_KEY = "novelguard.reviewGrid.sizing.v1";

/** TanStack table state: all columns enabled; render uses width-based merge. */
export const reviewGridAllColumnsVisible: Record<string, boolean> = {
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

export function buildReviewGridColumns(): ColumnDef<ReviewRow>[] {
  return [
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
