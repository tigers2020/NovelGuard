import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AppSnapshot } from "../../types/snapshot";
import { validAppSnapshot } from "../../contracts/fixtures";
import { ScanWorkspace } from "./ScanWorkspace";

vi.mock("../../app/providers/snapshotHooks", () => ({
  useBridge: () => ({ selectFolder: vi.fn() }),
  useRefreshSnapshot: () => vi.fn(),
}));

const noop = vi.fn();

function renderScanWorkspace(scan: AppSnapshot["work"]["scan"]) {
  const library = { ...validAppSnapshot.library, folderPath: "/tmp/library" };
  const pipeline = { ...validAppSnapshot.pipeline };
  render(
    <ScanWorkspace
      library={library}
      scan={scan}
      quality={validAppSnapshot.work.quality}
      pipeline={pipeline}
      onStartScan={noop}
      onCancelScan={noop}
      onOpenSettings={noop}
      onRevealFileDock={noop}
    />,
  );
}

describe("ScanWorkspace auto-approve summary (NOV-28)", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows summary when scan success and exactAutoApprovedCount > 0", () => {
    renderScanWorkspace({
      ...validAppSnapshot.work.scan,
      state: "success",
      exactAutoApprovedCount: 2,
      indexReady: true,
      lastRun: "2026-06-05T00:00:00Z",
    });

    const summary = screen.getByTestId("scan-auto-approve-summary");
    expect(summary.textContent).toContain("Exact 중복 2건 non-keeper 자동 승인");
  });

  it("hides summary when scan success and exactAutoApprovedCount is 0", () => {
    renderScanWorkspace({
      ...validAppSnapshot.work.scan,
      state: "success",
      exactAutoApprovedCount: 0,
      indexReady: true,
      lastRun: "2026-06-05T00:00:00Z",
    });

    expect(screen.queryByTestId("scan-auto-approve-summary")).toBeNull();
  });

  it("hides summary while scan is running even when count is positive", () => {
    renderScanWorkspace({
      ...validAppSnapshot.work.scan,
      state: "running",
      exactAutoApprovedCount: 3,
      indexReady: false,
    });

    expect(screen.queryByTestId("scan-auto-approve-summary")).toBeNull();
    expect(screen.getByTestId("scan-status-running")).toBeTruthy();
  });

  it("hides summary on scan error even when count is positive", () => {
    renderScanWorkspace({
      ...validAppSnapshot.work.scan,
      state: "error",
      exactAutoApprovedCount: 3,
      indexReady: true,
    });

    expect(screen.queryByTestId("scan-auto-approve-summary")).toBeNull();
    expect(screen.getByTestId("scan-status-error")).toBeTruthy();
  });
});
