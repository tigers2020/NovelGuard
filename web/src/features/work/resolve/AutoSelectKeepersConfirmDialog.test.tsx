import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AutoSelectKeepersConfirmDialog } from "./AutoSelectKeepersConfirmDialog";
import type { ResolveAutoApproveSummary } from "../../../types/resolveAutoApproveSummary";

const baseSummary: ResolveAutoApproveSummary = {
  unreviewedCount: 10,
  keeperCount: 4,
  moveCandidateCount: 6,
  exactCount: 3,
  nearCount: 4,
  relationCount: 3,
  skippedConflictCount: 0,
  skippedExcludedCount: 0,
  keeperRowIds: [],
  approveRowIds: [],
  samples: {
    keepers: [],
    moveCandidates: [],
    exact: [],
    near: [],
    relation: [],
  },
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
    expect(screen.getByTestId("auto-select-summary-keepers").textContent).toContain("4");
    expect(screen.getByTestId("auto-select-summary-move-candidates").textContent).toContain("6");
    expect(screen.getByText(/가장 용량이 큰 파일/)).toBeTruthy();
    expect(screen.getByText(/용량이 같으면 가장 최근 수정된 파일/)).toBeTruthy();
    expect(
      screen.getByText(/이동 계획 미리보기에서 최종 이동 대상을 검토합니다/),
    ).toBeTruthy();
    expect(screen.queryByTestId("bulk-auto-select-cap-warning")).toBeNull();
    expect(screen.queryByTestId("batch-partial-load-warning")).toBeNull();
  });
});
