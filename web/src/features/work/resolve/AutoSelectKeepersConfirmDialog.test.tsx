import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AutoSelectKeepersConfirmDialog } from "./AutoSelectKeepersConfirmDialog";
import type { AutoSelectKeepersStats } from "./autoSelectKeepers";

const baseStats: AutoSelectKeepersStats = {
  exactUnreviewed: 4,
  nearUnreviewed: 2,
  relationUnreviewed: 1,
  keeperCount: 3,
  moveCandidateCount: 4,
  unreviewedFileCount: 7,
};

describe("AutoSelectKeepersConfirmDialog", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders E/N/R counts and keeper rule", () => {
    render(
      <AutoSelectKeepersConfirmDialog
        open
        stats={baseStats}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("auto-select-keepers-confirm-dialog")).toBeTruthy();
    expect(screen.getByText(/Exact 4/)).toBeTruthy();
    expect(screen.getByText(/Near 2/)).toBeTruthy();
    expect(screen.getByText(/Relation 1/)).toBeTruthy();
    expect(screen.getByTestId("auto-select-keeper-rule").textContent).toContain("크기");
    expect(screen.queryByTestId("auto-select-cap-warning")).toBeNull();
  });

  it("shows cap warning when unreviewed count exceeds 500", () => {
    render(
      <AutoSelectKeepersConfirmDialog
        open
        stats={{ ...baseStats, unreviewedFileCount: 501, moveCandidateCount: 498 }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("auto-select-cap-warning")).toBeTruthy();
  });
});
