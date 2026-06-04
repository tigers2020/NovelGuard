import { useCallback, useEffect, useMemo, useState } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import { StatChip } from "../../components/ui/StatChip";
import type {
  FinalizeCleanupResult,
  FinalizeReportDocument,
  FinalizeResult,
  FinalizeSummary,
} from "../../types/finalize";
import { FinalizeReportPanel } from "./FinalizeReportPanel";

type SectionState = "empty" | "ready" | "warning" | "disabled" | "running" | "success" | "error";

function deriveSectionState(
  hasLibrary: boolean,
  pipelinePhase: string,
  summary: FinalizeSummary | null,
  lastStatus: string,
): SectionState {
  if (!hasLibrary) {
    return "empty";
  }
  if (pipelinePhase === "finalize") {
    return "running";
  }
  if (lastStatus === "error") {
    return "error";
  }
  if (lastStatus === "complete") {
    return "success";
  }
  if (lastStatus === "complete_with_warnings") {
    return "warning";
  }
  if (summary && summary.blockers.length > 0) {
    return "disabled";
  }
  if (summary && summary.warnings.length > 0) {
    return "warning";
  }
  return "ready";
}

export function FinalizeSubflowContent({
  compact = false,
  onOpenLogs,
}: {
  compact?: boolean;
  onOpenLogs?: () => void;
}) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const refreshSnapshot = useRefreshSnapshot();
  const [summary, setSummary] = useState<FinalizeSummary | null>(null);
  const [includeCleanup, setIncludeCleanup] = useState(false);
  const [cleanupPreview, setCleanupPreview] = useState<string[] | null>(null);
  const [lastCleanup, setLastCleanup] = useState<FinalizeCleanupResult | null>(null);
  const [report, setReport] = useState<FinalizeReportDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasLibrary = Boolean(snapshot.library.folderPath);
  const finalize = snapshot.work.finalize;

  const loadSummary = useCallback(async () => {
    if (!hasLibrary) {
      setSummary(null);
      return;
    }
    try {
      const next = await bridge.getFinalizeSummary();
      setSummary(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [bridge, hasLibrary]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadSummary();
    });
    return () => cancelAnimationFrame(frame);
  }, [loadSummary, snapshot.work.resolve.libraryRevision, finalize.lastStatus]);

  const blockers = summary?.blockers ?? [];
  const warnings = summary?.warnings ?? [];
  const cleanupPreviewActive = includeCleanup && hasLibrary && blockers.length === 0;

  useEffect(() => {
    if (!cleanupPreviewActive) {
      return;
    }
    let cancelled = false;
    void bridge
      .previewFinalizeCleanup()
      .then((preview) => {
        if (!cancelled) {
          setCleanupPreview(preview.previewedEmptyDirs);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [bridge, cleanupPreviewActive]);

  const sectionState = deriveSectionState(
    hasLibrary,
    snapshot.pipeline.phase,
    summary,
    finalize.lastStatus,
  );

  const primaryDisabled =
    !hasLibrary ||
    busy ||
    sectionState === "running" ||
    sectionState === "disabled" ||
    blockers.length > 0;
  const cleanupDisabled = primaryDisabled;
  const primaryTooltip = blockers[0]?.message;

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const result: FinalizeResult = await bridge.runFinalizeVerification({ includeCleanup });
      setLastCleanup(result.cleanup);
      await refreshSnapshot();
      await loadSummary();
      if (result.reportId) {
        const doc = await bridge.getFinalizeReport(result.reportId);
        setReport(doc);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const onViewReport = async () => {
    if (!finalize.lastReportId) {
      return;
    }
    try {
      const doc = await bridge.getFinalizeReport(finalize.lastReportId);
      setReport(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const statusLabel = useMemo(() => {
    switch (sectionState) {
      case "empty":
        return "라이브러리 없음";
      case "running":
        return "검증 실행 중";
      case "disabled":
        return "차단됨";
      case "warning":
        return "경고 포함";
      case "success":
        return "완료";
      case "error":
        return "오류";
      default:
        return "준비됨";
    }
  }, [sectionState]);

  return (
    <div
      className={compact ? "space-y-4" : "mx-auto max-w-6xl space-y-4"}
      data-testid="finalize-subflow-content"
      data-state={sectionState}
    >
      <section className="rounded-md border border-outline bg-surface p-5">
        <p className="text-xs font-semibold text-secondary">Finalize</p>
        <h1 className="mt-1 text-2xl font-bold text-on-surface">적용 · 검증</h1>
        <p className="mt-2 text-sm text-on-surface-variant">
          정리 후 라이브러리 상태를 검증하고 완료 보고서를 저장합니다.
        </p>
        <p className="mt-1 text-xs text-muted">
          상태: {statusLabel}
          {sectionState === "running" ? ` · ${snapshot.pipeline.label}` : ""}
        </p>
      </section>

      {summary && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatChip label="Scan" value={summary.scanState} />
          <StatChip
            label="Exact queue"
            value={String(summary.resolve.exactUnresolvedQueueCount)}
          />
          <StatChip
            label="Quality errors"
            value={String(summary.quality.encodingIssueCount + summary.quality.integrityIssueCount)}
          />
          <StatChip label="Last run" value={finalize.lastRunAt ?? "—"} />
        </section>
      )}

      {blockers.length > 0 && (
        <section className="rounded-md border border-error/40 bg-surface p-4">
          <h2 className="text-sm font-semibold text-error">차단 사유</h2>
          <ul className="mt-2 space-y-1 text-sm text-on-surface">
            {blockers.map((item) => (
              <li key={item.code}>
                {item.message}
                {item.count != null ? ` (${item.count})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {warnings.length > 0 && (
        <section className="rounded-md border border-secondary/40 bg-surface p-4">
          <h2 className="text-sm font-semibold text-secondary">경고</h2>
          <ul className="mt-2 space-y-1 text-sm text-on-surface">
            {warnings.map((item) => (
              <li key={item.code}>
                {item.message}
                {item.count != null ? ` (${item.count})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-4 rounded-md border border-outline bg-surface p-5">
        <label className="flex items-start gap-3 text-sm text-on-surface">
          <input
            type="checkbox"
            className="mt-1"
            data-testid="finalize-cleanup-checkbox"
            checked={includeCleanup}
            disabled={cleanupDisabled}
            onChange={(e) => {
              const checked = e.target.checked;
              setIncludeCleanup(checked);
              if (!checked) {
                setCleanupPreview(null);
              }
            }}
          />
          <span>
            <span className="font-semibold">라이브러리 안 빈 출력 폴더(duplicate/, organized/) 삭제</span>
            <span className="mt-1 block text-xs text-muted">
              파일은 삭제하지 않습니다. 이동본은 라이브러리 옆 «이름_duplicate» 폴더에 있으며, 여기서는
              라이브러리 내부의 빈 폴더만 정리합니다.
            </span>
          </span>
        </label>

        {cleanupPreviewActive && cleanupPreview !== null && (
          <div
            className="rounded-md border border-outline bg-background px-3 py-2 text-sm"
            data-testid="finalize-cleanup-preview"
          >
            <p className="font-semibold text-on-surface">정리 미리보기</p>
            {cleanupPreview.length === 0 ? (
              <p className="mt-1 text-muted">삭제 대상 빈 폴더가 없습니다.</p>
            ) : (
              <ul className="mt-1 max-h-32 list-inside list-disc overflow-y-auto font-mono text-xs text-on-surface-variant">
                {cleanupPreview.map((dir) => (
                  <li key={dir}>{dir}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="finalize-run-button"
            disabled={primaryDisabled}
            title={primaryTooltip}
            onClick={() => void onRun()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-background disabled:cursor-not-allowed disabled:opacity-50"
          >
            최종 검증 실행
          </button>
          <button
            type="button"
            data-testid="finalize-report-button"
            disabled={!finalize.lastReportId}
            onClick={() => void onViewReport()}
            className="rounded-md border border-outline px-4 py-2 text-sm font-semibold text-on-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            완료 보고서 보기
          </button>
          {onOpenLogs && finalize.lastReportId && (
            <button
              type="button"
              data-testid="finalize-open-logs"
              onClick={onOpenLogs}
              className="rounded-md border border-outline px-4 py-2 text-sm font-semibold text-on-surface hover:bg-hover"
            >
              로그 · 산출물
            </button>
          )}
        </div>

        {error && <p className="text-sm text-error">{error}</p>}
      </section>

      {lastCleanup && (
        <section
          className="rounded-md border border-outline bg-surface p-4"
          data-testid="finalize-cleanup-result"
        >
          <h2 className="text-sm font-semibold text-on-surface">정리 결과</h2>
          <p className="mt-1 text-xs text-muted">
            미리보기 {lastCleanup.previewedEmptyDirs.length}개 · 삭제{" "}
            {lastCleanup.removedEmptyDirs.length}개
          </p>
          {lastCleanup.removedEmptyDirs.length > 0 && (
            <ul className="mt-2 max-h-32 list-inside list-disc overflow-y-auto font-mono text-xs text-on-surface-variant">
              {lastCleanup.removedEmptyDirs.map((dir) => (
                <li key={dir}>{dir}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {report && <FinalizeReportPanel report={report} />}
    </div>
  );
}

export function FinalizeWorkspace() {
  return (
    <main
      className="h-full overflow-y-auto bg-background p-5"
      data-testid="finalize-workspace"
    >
      <FinalizeSubflowContent />
    </main>
  );
}
