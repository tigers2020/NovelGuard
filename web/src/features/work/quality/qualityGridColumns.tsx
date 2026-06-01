import { createColumnHelper } from "@tanstack/react-table";
import type { QualityRow } from "../../../types/quality";

const helper = createColumnHelper<QualityRow>();

import type { ColumnDef } from "@tanstack/react-table";

export function buildQualityGridColumns(): ColumnDef<QualityRow>[] {
  return [
    helper.accessor("name", {
      header: "Name",
      enableSorting: true,
      meta: { gridWidth: "minmax(0,1fr)" },
      cell: (ctx) => (
        <span className="truncate font-medium text-on-surface">{ctx.getValue()}</span>
      ),
    }),
    helper.accessor("encoding", {
      header: "Encoding",
      enableSorting: true,
      meta: { gridWidth: "6rem" },
      cell: (ctx) => <span className="text-secondary">{ctx.getValue() ?? "—"}</span>,
    }),
    helper.accessor("integrity", {
      header: "Integrity",
      enableSorting: true,
      meta: { gridWidth: "8rem" },
      cell: (ctx) => {
        const row = ctx.row.original;
        return (
          <span className={row.severity === "error" ? "text-error" : "text-muted"}>
            {ctx.getValue()}
          </span>
        );
      },
    }),
  ] as ColumnDef<QualityRow>[];
}
