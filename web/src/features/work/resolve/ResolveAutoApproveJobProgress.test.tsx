import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { idleResolveAutoApproveJobSnapshot } from "../../../types/resolveAutoApproveJob";
import { ResolveAutoApproveJobProgress } from "./ResolveAutoApproveJobProgress";

describe("ResolveAutoApproveJobProgress", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders nothing when job is idle", () => {
    const { container } = render(
      <ResolveAutoApproveJobProgress job={idleResolveAutoApproveJobSnapshot()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows running status, phase, and cancel", () => {
    render(
      <ResolveAutoApproveJobProgress
        job={{
          ...idleResolveAutoApproveJobSnapshot(),
          status: "running",
          phase: "approve",
          processedRows: 12,
          totalRows: 40,
          scannedCount: 40,
          eligibleCount: 35,
          keeperSetCount: 5,
          approvedRowCount: 7,
          label: "승인 처리 중…",
        }}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("resolve-auto-approve-status").textContent).toContain("진행 중");
    expect(screen.getByTestId("resolve-auto-approve-phase").textContent).toBe("approve");
    expect(screen.getByTestId("resolve-auto-approve-row-progress").textContent).toContain("12");
    expect(screen.getByTestId("resolve-auto-approve-cancel")).toBeTruthy();
  });

  it("shows error message when job failed", () => {
    render(
      <ResolveAutoApproveJobProgress
        job={{
          ...idleResolveAutoApproveJobSnapshot(),
          status: "error",
          error: "sqlite busy",
        }}
      />,
    );

    expect(screen.getByTestId("resolve-auto-approve-status").textContent).toContain("실패");
    expect(screen.getByTestId("resolve-auto-approve-error").textContent).toBe("sqlite busy");
    expect(screen.queryByTestId("resolve-auto-approve-cancel")).toBeNull();
  });
});
