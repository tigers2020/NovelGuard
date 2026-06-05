import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BatchActionBar } from "./BatchActionBar";

const noop = vi.fn();

describe("BatchActionBar", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows loading-all badge while loadingAll", () => {
    render(
      <BatchActionBar
        filteredCount={500}
        loadedCount={200}
        loadingAll
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.getByTestId("batch-loading-all").textContent).toContain("전체 로드 중");
    expect(screen.queryByTestId("batch-partial-load-warning")).toBeNull();
  });

  it("shows partial-load warning when not loadingAll and loaded < filtered", () => {
    render(
      <BatchActionBar
        filteredCount={500}
        loadedCount={200}
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-loading-all")).toBeNull();
    expect(screen.getByTestId("batch-partial-load-warning").textContent).toContain("일부만 로드됨");
  });

  it("hides partial warning when loaded equals filtered", () => {
    render(
      <BatchActionBar
        filteredCount={500}
        loadedCount={500}
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-partial-load-warning")).toBeNull();
  });
});
