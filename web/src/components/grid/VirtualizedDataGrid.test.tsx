import { render } from "@testing-library/react";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";
import { VirtualizedDataGrid } from "./VirtualizedDataGrid";
import { maxRenderedRowSlots } from "./virtualWindow";

type Row = { id: string; name: string };

const helper = createColumnHelper<Row>();
const columns = [
  helper.accessor("name", { header: "Name", meta: { gridWidth: "1fr" } }),
] as ColumnDef<Row>[];

describe("VirtualizedDataGrid perf", () => {
  it("renders bounded DOM rows for 2000 logical rows", () => {
    const data = Array.from({ length: 2000 }, (_, i) => ({ id: `r-${i}`, name: `Row ${i}` }));
    const { container } = render(
      <div style={{ height: 400, width: 800, display: "flex" }}>
        <VirtualizedDataGrid
          testId="perf-grid"
          data={data}
          columns={columns}
          getRowId={(r) => r.id}
          overscan={8}
        />
      </div>,
    );
    const domRows = container.querySelectorAll('[data-testid="grid-row"]');
    expect(domRows.length).toBeLessThanOrEqual(maxRenderedRowSlots({ overscan: 8 }));
  });
});
