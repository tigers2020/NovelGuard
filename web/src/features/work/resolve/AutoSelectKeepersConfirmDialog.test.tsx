import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AutoSelectKeepersConfirmDialog } from "./AutoSelectKeepersConfirmDialog";
import type { AutoSelectSummary } from "./computeAutoSelectSummary";

const baseSummary: AutoSelectSummary = {
  unreviewedCount: 10,
  keeperCount: 4,
  moveCandidateCount: 6,
  exactCount: 3,
  nearCount: 4,
  relationCount: 3,
  capped: false,
  mutationTargetCount: 10,
  partialLoad: false,
  keeperPreviewUsesMtime: true,
};

describe("AutoSelectKeepersConfirmDialog", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders canonical sections and count testids", () => {
    render(
      <AutoSelectKeepersConfirmDialog
        open
        summary={baseSummary}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("auto-select-keepers-confirm-dialog")).toBeTruthy();
    expect(screen.getByText(/미검토 10건을 자동 선정합니다/)).toBeTruthy();
    expect(screen.getByTestId("auto-select-summary-exact").textContent).toContain("3");
    expect(screen.getByTestId("auto-select-summary-near").textContent).toContain("4");
    expect(screen.getByTestId("auto-select-summary-relation").textContent).toContain("3");
    expect(screen.getByText(/가장 용량이 큰 파일/)).toBeTruthy();
    expect(
      screen.getByText(/이동 계획 미리보기에서 최종 이동 대상을 검토합니다/),
    ).toBeTruthy();
    expect(screen.queryByTestId("bulk-auto-select-cap-warning")).toBeNull();
  });

  it("shows cap warning when capped", () => {
    render(
      <AutoSelectKeepersConfirmDialog
        open
        summary={{
          ...baseSummary,
          capped: true,
          mutationTargetCount: 500,
          unreviewedCount: 501,
        }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("bulk-auto-select-cap-warning")).toBeTruthy();
    expect(screen.getByText(/500건을 초과합니다/)).toBeTruthy();
  });

  it("shows partial load warning when partialLoad", () => {
    render(
      <AutoSelectKeepersConfirmDialog
        open
        summary={{ ...baseSummary, partialLoad: true }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("batch-partial-load-warning")).toBeTruthy();
  });
});
