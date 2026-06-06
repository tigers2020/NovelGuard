import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RecoveryState, UndoDryRunPlan, UndoExecutionResult } from "../../types/recovery";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { RecoveryUndoSubflowDialog } from "./RecoveryUndoSubflowDialog";

const previewUndoPlan = vi.fn();
const executeUndoPlan = vi.fn();
const refreshSnapshot = vi.fn(async () => {});
const onRecoveryRefreshed = vi.fn(async () => {});
const onClose = vi.fn();

vi.mock("../../app/providers/snapshotHooks", () => ({
  useBridge: () => ({
    previewUndoPlan,
    executeUndoPlan,
  }),
  useRefreshSnapshot: () => refreshSnapshot,
}));

const recoveryState: RecoveryState = {
  hasActivePlan: true,
  undoPlanId: "plan-1",
  runId: "run-1",
  batchKind: "move_apply",
  manifestStatus: "pending",
  appliedCount: 2,
  recoverableCount: 2,
  manualRequiredCount: 0,
  blockedCount: 0,
  unrecoverableCount: 0,
  sealedAt: null,
};

const previewPlan: UndoDryRunPlan = {
  undoPlanId: "plan-1",
  manifestPath: null,
  libraryId: "lib-1",
  runId: "run-1",
  totalCount: 2,
  recoverableCount: 2,
  blockedCount: 0,
  manualRequiredCount: 0,
  items: [
    {
      operationId: "op-1",
      sequence: 1,
      fromPath: "a.txt",
      toPath: "b.txt",
      status: "recoverable",
      reason: null,
    },
  ],
  previewToken: "token-abc",
};

const executionResult: UndoExecutionResult = {
  undoPlanId: "plan-1",
  manifestStatus: "completed",
  noOp: false,
  recoveredCount: 2,
  alreadyRecoveredCount: 0,
  failedCount: 0,
  excludedCount: 0,
  items: [],
};

describe("RecoveryUndoSubflowDialog", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("execute is impossible without preview token", () => {
    render(
      <RecoveryUndoSubflowDialog
        open
        recoveryState={recoveryState}
        onClose={onClose}
        onRecoveryRefreshed={onRecoveryRefreshed}
      />,
    );
    expect(screen.queryByTestId("recovery-undo-execute-run")).toBeNull();
  });

  it("preview success enables confirmation and execute", async () => {
    previewUndoPlan.mockResolvedValueOnce(previewPlan);
    render(
      <RecoveryUndoSubflowDialog
        open
        recoveryState={recoveryState}
        onClose={onClose}
        onRecoveryRefreshed={onRecoveryRefreshed}
      />,
    );

    fireEvent.click(screen.getByTestId("recovery-undo-preview-run"));
    await waitFor(() => {
      expect(screen.getByTestId("recovery-undo-preview-summary")).toBeTruthy();
    });

    const executeBtn = screen.getByTestId("recovery-undo-execute-run") as HTMLButtonElement;
    expect(executeBtn.disabled).toBe(true);
    fireEvent.click(screen.getByTestId("recovery-undo-confirm-checkbox"));
    expect(executeBtn.disabled).toBe(false);
  });

  it("stale preview error asks user to re-preview", async () => {
    previewUndoPlan.mockResolvedValueOnce(previewPlan);
    executeUndoPlan.mockRejectedValueOnce(
      new BridgeCallError("rejected", {
        code: "rejected",
        method: "execute_undo_plan",
        reason: "STALE_UNDO_PREVIEW",
      }),
    );

    render(
      <RecoveryUndoSubflowDialog
        open
        recoveryState={recoveryState}
        onClose={onClose}
        onRecoveryRefreshed={onRecoveryRefreshed}
      />,
    );

    fireEvent.click(screen.getByTestId("recovery-undo-preview-run"));
    await waitFor(() => {
      expect(screen.getByTestId("recovery-undo-confirm-checkbox")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("recovery-undo-confirm-checkbox"));
    fireEvent.click(screen.getByTestId("recovery-undo-execute-run"));

    await waitFor(() => {
      expect(screen.getByTestId("recovery-undo-execute-error").textContent).toMatch(
        /다시 미리보기/,
      );
    });
    expect(screen.getByTestId("recovery-undo-preview-run")).toBeTruthy();
    expect(screen.queryByTestId("recovery-undo-execute-run")).toBeNull();
  });

  it("terminal execute refreshes recovery state", async () => {
    previewUndoPlan.mockResolvedValueOnce(previewPlan);
    executeUndoPlan.mockResolvedValueOnce(executionResult);

    render(
      <RecoveryUndoSubflowDialog
        open
        recoveryState={recoveryState}
        onClose={onClose}
        onRecoveryRefreshed={onRecoveryRefreshed}
      />,
    );

    fireEvent.click(screen.getByTestId("recovery-undo-preview-run"));
    await waitFor(() => {
      expect(screen.getByTestId("recovery-undo-confirm-checkbox")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("recovery-undo-confirm-checkbox"));
    fireEvent.click(screen.getByTestId("recovery-undo-execute-run"));

    await waitFor(() => {
      expect(screen.getByTestId("recovery-undo-done")).toBeTruthy();
    });
    expect(refreshSnapshot).toHaveBeenCalled();
    expect(onRecoveryRefreshed).toHaveBeenCalled();
  });
});
