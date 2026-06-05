import { useState } from "react";
import { useBridge, useRefreshSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { formatBytes } from "../../lib/format";
import type { AppSnapshot, PipelineSnapshot } from "../../types/snapshot";
import { StatChip } from "../../components/ui/StatChip";
import { deriveScanSectionState } from "./scanSectionState";

function folderPickerErrorMessage(err: unknown): string {
  if (err instanceof BridgeCallError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Folder selection failed";
}

export function ScanWorkspace({
  library,
  scan,
  quality,
  pipeline,
  onStartScan,
  onCancelScan,
  onOpenSettings,
  onRevealFileDock,
}: {
  library: AppSnapshot["library"];
  scan: AppSnapshot["work"]["scan"];
  quality: AppSnapshot["work"]["quality"];
  pipeline: PipelineSnapshot;
  onStartScan: () => void;
  onCancelScan: () => void;
  onOpenSettings: () => void;
  onRevealFileDock: () => void;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const [isSelecting, setIsSelecting] = useState(false);
  const [folderError, setFolderError] = useState<string | null>(null);

  const sectionState = deriveScanSectionState({ folderPath: library.folderPath, scan, pipeline });
  const scanRunning = sectionState === "running";
  const folderPath = library.folderPath ?? "폴더 미선택";
  const canStartScan = Boolean(library.folderPath) && !scanRunning;
  const scanPrimaryLabel = scan.state === "success" ? "다시 스캔" : "스캔 시작";
  const canOpenFileDock =
    Boolean(library.folderPath) && (scan.indexReady || library.fileCount > 0);
  const showSummary =
    Boolean(library.folderPath) &&
    (sectionState !== "running" || scan.indexReady || library.fileCount > 0);

  const handleSelectFolder = async () => {
    setIsSelecting(true);
    setFolderError(null);
    try {
      await bridge.selectFolder();
      await refreshSnapshot();
    } catch (err) {
      setFolderError(folderPickerErrorMessage(err));
    } finally {
      setIsSelecting(false);
    }
  };

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background"
      data-testid="scan-workspace"
    >
      <section
        data-testid="scan-section"
        data-state={sectionState}
        className="shrink-0 border-b border-outline bg-surface px-4 py-3 data-[state=empty]:border-dashed"
      >
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold text-secondary">Scan / Import</p>
          {showSummary && (
            <div
              className="flex flex-wrap items-center gap-2"
              data-testid="scan-summary"
            >
              <StatChip label="Files" value={library.fileCount.toLocaleString()} />
              <StatChip label="Size" value={formatBytes(library.totalBytes)} />
              <StatChip label="Encoding" value={quality.encodingIssueCount.toLocaleString()} />
              <StatChip label="Last run" value={scan.lastRun ?? library.lastRun ?? "—"} />
            </div>
          )}
          {sectionState === "success" && scan.exactAutoApprovedCount > 0 && (
            <p
              className="w-full text-sm text-on-surface-variant"
              role="status"
              data-testid="scan-auto-approve-summary"
            >
              Exact 중복 {scan.exactAutoApprovedCount}건 non-keeper 자동 승인 — 검토·정리에서 이동 계획
              미리보기 가능
            </p>
          )}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p
            className="min-w-[12rem] flex-1 truncate rounded-md border border-outline bg-background px-3 py-1.5 text-sm text-on-surface-variant"
            aria-live="polite"
            title={library.folderPath ?? undefined}
          >
            {folderPath}
          </p>
          <button
            type="button"
            data-testid="scan-select-folder"
            disabled={isSelecting || scanRunning}
            onClick={() => void handleSelectFolder()}
            className="shrink-0 rounded-md border border-outline px-3 py-1.5 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSelecting ? "선택 중…" : "폴더 선택"}
          </button>
        </div>

        {folderError && (
          <p
            className="mt-2 rounded-md border border-error/40 bg-error/10 px-3 py-2 text-sm text-error"
            data-testid="scan-folder-error"
            role="alert"
          >
            {folderError}
          </p>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-secondary">스캔 옵션</span>
          <button
            type="button"
            data-testid="scan-open-settings"
            onClick={onOpenSettings}
            className="text-xs font-semibold text-primary underline-offset-2 hover:underline"
          >
            스캔 설정…
          </button>
          {library.scanOptions.length > 0 ? (
            library.scanOptions.map((option) => (
              <span
                key={option}
                className="rounded-full border border-outline bg-background px-2 py-0.5 text-xs text-on-surface-variant"
              >
                {option}
              </span>
            ))
          ) : (
            <span className="text-xs text-muted">기본값</span>
          )}
        </div>

        {sectionState === "running" && (
          <p className="mt-2 text-sm text-on-surface-variant" data-testid="scan-status-running">
            스캔 진행 중 — {pipeline.label} ({pipeline.percent}%)
          </p>
        )}
        {sectionState === "error" && (
          <p
            className="mt-2 rounded-md border border-error/40 bg-error/10 px-3 py-2 text-sm text-error"
            data-testid="scan-status-error"
            role="alert"
          >
            스캔 중 오류가 발생했습니다. 로그에서 자세한 내용을 확인하세요.
          </p>
        )}
        {scan.deepAnalysisStatus === "error" && (
          <p
            className="mt-2 rounded-md border border-error/40 bg-error/10 px-3 py-2 text-sm text-error"
            data-testid="deep-analysis-error"
            role="alert"
          >
            후속 분석 중 오류가 발생했습니다.
            {scan.deepAnalysisError ? ` ${scan.deepAnalysisError}` : null}
          </p>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="scan-start"
            disabled={!canStartScan}
            onClick={onStartScan}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {scanPrimaryLabel}
          </button>
          {scanRunning && (
            <button
              type="button"
              data-testid="scan-cancel"
              onClick={onCancelScan}
              className="rounded-md border border-error/40 bg-error/20 px-3 py-1.5 text-sm font-semibold text-error hover:bg-error/30"
            >
              스캔 취소
            </button>
          )}
          {canOpenFileDock && (
            <button
              type="button"
              data-testid="scan-open-file-dock"
              onClick={onRevealFileDock}
              className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
            >
              파일 목록 펼치기
            </button>
          )}
        </div>
      </section>
    </main>
  );
}
