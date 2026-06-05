import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResolveGridToolbar } from "./ResolveGridToolbar";

const noop = vi.fn();

function renderToolbar(rowTypeFilter: "exact" | "near" | "relation" | "all" = "exact") {
  render(
    <ResolveGridToolbar
      queueCount={1}
      groupCount={2}
      conflictCount={0}
      approvedCount={3}
      rowTypeFilter={rowTypeFilter}
      onRowTypeFilterChange={noop}
      search=""
      onSearchChange={noop}
      loading={false}
      queryError={null}
      onRetry={noop}
      onOpenFinalize={noop}
    />,
  );
}

describe("ResolveGridToolbar type filter labels (NOV-29)", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows KO tab hints for exact, near, and relation filters", () => {
    renderToolbar();

    expect(screen.getByTestId("resolve-type-filter-exact").textContent).toBe("Exact (이동)");
    expect(screen.getByTestId("resolve-type-filter-near").textContent).toBe("Near (참고)");
    expect(screen.getByTestId("resolve-type-filter-relation").textContent).toBe("Relation (참고)");
    expect(screen.getByTestId("resolve-type-filter-all").textContent).toBe("All types");
  });
});
