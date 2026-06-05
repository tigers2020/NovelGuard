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
        onAutoSelectKeepers={noop}
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
        onAutoSelectKeepers={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-loading-all")).toBeNull();
    expect(screen.getByTestId("batch-partial-load-warning").textContent).toContain("일부만 로드됨");
  });

  it("shows review-only banner when guidance provided", () => {
    render(
      <BatchActionBar
        filteredCount={10}
        loadedCount={10}
        reviewOnlyGuidance="Near 중복은 검토 전용이며 일괄 적용할 수 없습니다."
        onExcludeAllFiltered={noop}
        onAutoSelectKeepers={noop}
        onPreview={noop}
      />,
    );

    expect(screen.getByTestId("batch-review-only-banner").textContent).toContain("검토 전용");
  });

  it("hides partial warning when loaded equals filtered", () => {
    render(
      <BatchActionBar
        filteredCount={500}
        loadedCount={500}
        onExcludeAllFiltered={noop}
        onAutoSelectKeepers={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-partial-load-warning")).toBeNull();
  });

  it("shows review-only banner when guidance is set", () => {
    render(
      <BatchActionBar
        filteredCount={10}
        loadedCount={10}
        reviewOnlyGuidance="Exact (이동) 탭에서만 가능합니다."
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.getByTestId("batch-review-only-banner").textContent).toContain("Exact (이동)");
  });

  it("hides review-only banner when guidance is unset", () => {
    render(
      <BatchActionBar
        filteredCount={10}
        loadedCount={10}
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-review-only-banner")).toBeNull();
  });
});
