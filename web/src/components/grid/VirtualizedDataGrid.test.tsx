import { render } from "@testing-library/react";
import { createColumnHelper, type ColumnDef } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";
import { mergeReviewColumnVisibility } from "../../features/work/resolve/reviewGridLayout";
import { buildReviewGridColumns } from "../../features/work/resolve/reviewGridColumns";
import type { ReviewRow } from "../../types/review";
import { VirtualizedDataGrid } from "./VirtualizedDataGrid";
import { parseRemWidthToPx } from "./gridColumnWidths";
import { maxRenderedRowSlots } from "./virtualWindow";

type Row = { id: string; name: string };

const helper = createColumnHelper<Row>();
const columns = [
  helper.accessor("name", { header: "Name", meta: { gridWidth: "1fr" } }),
] as ColumnDef<Row>[];

describe("mergeReviewColumnVisibility", () => {
  it("hides columns progressively when viewport is narrow", () => {
    const narrow = mergeReviewColumnVisibility(280);
    expect(narrow.name).toBe(true);
    expect(narrow.status).toBe(true);
    expect(narrow.proposedAction).toBe(false);
    expect(narrow.encoding).toBe(false);

    const wide = mergeReviewColumnVisibility(800);
    expect(wide.proposedAction).toBe(true);
    expect(wide.confidence).toBe(true);
    expect(wide.encoding).toBe(true);
    expect(wide.path).toBe(true);
    expect(wide.sizeBytes).toBe(true);
  });

  it("shows optional columns only when scrollport is wide enough", () => {
    expect(mergeReviewColumnVisibility(500).encoding).toBe(false);
    expect(mergeReviewColumnVisibility(550).encoding).toBe(true);
  });

  it("keeps only name visible before layout width is known", () => {
    const narrow = mergeReviewColumnVisibility(0);
    expect(narrow.name).toBe(true);
    expect(narrow.status).toBe(false);
    expect(narrow.encoding).toBe(false);
    expect(mergeReviewColumnVisibility(100).encoding).toBe(false);
  });
});

describe("gridColumnWidths", () => {
  it("parses rem widths to px", () => {
    expect(parseRemWidthToPx("5rem")).toBe(80);
    expect(parseRemWidthToPx("4.5rem")).toBe(72);
  });
});

describe("VirtualizedDataGrid review columns", () => {
  it("renders core review headers with expected test ids", () => {
    const row: ReviewRow = {
      id: "r1",
      rowKind: "file",
      hasChildren: false,
      status: "unreviewed",
      type: "exact",
      name: "sample.txt",
      keeperLabel: "keeper",
      proposedAction: "keep",
      targetFolder: "dup/",
      confidence: 0.9,
    };
    const { container } = render(
      <div style={{ height: 400, width: 900, display: "flex" }}>
        <VirtualizedDataGrid
          testId="review-grid"
          headerTestIdPrefix="resolve-grid-header"
          data={[row]}
          columns={buildReviewGridColumns()}
          getRowId={(r) => r.id}
          mergeColumnVisibility={() => mergeReviewColumnVisibility(900)}
          enableColumnResize
        />
      </div>,
    );
    expect(container.querySelector('[data-testid="resolve-grid-header-status"]')).not.toBeNull();
    expect(
      container.querySelector('[data-testid="resolve-grid-header-proposedAction"]'),
    ).not.toBeNull();
  });
});

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
