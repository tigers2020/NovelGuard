import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import type { QualityIssueType, QualityRow } from "../../../types/quality";

const helper = createColumnHelper<QualityRow>();

export const QUALITY_GRID_COLUMNS_KEY = "novelguard.qualityGrid.columns.v1";
export const QUALITY_GRID_SIZING_KEY = "novelguard.qualityGrid.sizing.v1";

export const OPTIONAL_QUALITY_COLUMN_KEYS = [
  "severity",
  "encoding",
  "integrity",
  "path",
  "issueType",
] as const;

export const qualityGridDefaultVisibility: Record<string, boolean> = {
  name: true,
  severity: true,
  encoding: true,
  integrity: true,
  path: false,
  issueType: false,
};

const ISSUE_TYPE_LABEL: Record<QualityIssueType, string> = {
  integrity: "무결성",
  encoding: "인코딩",
  small_file: "소형",
};

export function buildQualityGridColumns(): ColumnDef<QualityRow>[] {
  return [
    helper.accessor("name", {
      id: "name",
      header: "Name",
      enableSorting: true,
      meta: { gridWidth: "minmax(0,1fr)", minWidthPx: 160, resizable: true },
      cell: (ctx) => (
        <span className="truncate font-medium text-on-surface">{ctx.getValue()}</span>
      ),
    }),
    helper.accessor("severity", {
      header: "Severity",
      enableSorting: true,
      meta: { gridWidth: "5.5rem", minWidthPx: 64, resizable: true },
      cell: (ctx) => {
        const value = ctx.getValue();
        return (
          <span className={value === "error" ? "font-semibold text-error" : "text-warning"}>
            {value}
          </span>
        );
      },
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
      cell: (ctx) => {
        const row = ctx.row.original;
        return (
          <span className={row.severity === "error" ? "text-error" : "text-muted"}>
            {ctx.getValue()}
          </span>
        );
      },
    }),
    helper.accessor((row) => row.path ?? "—", {
      id: "path",
      header: "Path",
      enableSorting: true,
      meta: { gridWidth: "minmax(0,1.2fr)", minWidthPx: 120, resizable: true },
      cell: (ctx) => <span className="truncate text-xs text-muted">{String(ctx.getValue())}</span>,
    }),
    helper.accessor("issueType", {
      header: "Type",
      enableSorting: true,
      meta: { gridWidth: "5.5rem", minWidthPx: 56, resizable: true },
      cell: (ctx) => (
        <span className="text-on-surface-variant">{ISSUE_TYPE_LABEL[ctx.getValue()]}</span>
      ),
    }),
  ] as ColumnDef<QualityRow>[];
}
