import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EMPTY_RECOVERY_STATE } from "../../contracts/recoveryContract";
import type { RecoveryState } from "../../types/recovery";
import { RecoveryUndoBanner } from "./RecoveryUndoBanner";

vi.mock("./RecoveryUndoSubflowDialog", () => ({
  RecoveryUndoSubflowDialog: () => null,
}));

const refresh = vi.fn(async () => {});

function activeRecovery(overrides: Partial<RecoveryState> = {}): RecoveryState {
  return {
    ...EMPTY_RECOVERY_STATE,
    hasActivePlan: true,
    undoPlanId: "plan-1",
    runId: "run-1",
    batchKind: "move_apply",
    manifestStatus: "pending",
    appliedCount: 3,
    recoverableCount: 2,
    blockedCount: 1,
    ...overrides,
  };
}

describe("RecoveryUndoBanner", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("hides banner when no active plan", () => {
    render(
      <RecoveryUndoBanner
        recoveryState={EMPTY_RECOVERY_STATE}
        onRecoveryRefreshed={refresh}
      />,
    );
    expect(screen.queryByTestId("recovery-undo-banner")).toBeNull();
  });

  it("shows banner when active plan exists", () => {
    render(
      <RecoveryUndoBanner recoveryState={activeRecovery()} onRecoveryRefreshed={refresh} />,
    );
    expect(screen.getByTestId("recovery-undo-banner")).toBeTruthy();
    expect(screen.getByText(/복구 가능 2건/)).toBeTruthy();
  });

  it("disables open action while undo is executing", () => {
    render(
      <RecoveryUndoBanner
        recoveryState={activeRecovery({ manifestStatus: "executing" })}
        onRecoveryRefreshed={refresh}
      />,
    );
    const openBtn = screen.getByTestId("recovery-undo-open-dialog") as HTMLButtonElement;
    expect(openBtn.disabled).toBe(true);
  });
});
