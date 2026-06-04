import type { QualityIssueDetail, QualityIssueType, QualityRow } from "../../../types/quality";

const issueTypeLabels: Record<QualityIssueType, string> = {
  integrity: "무결성",
  encoding: "인코딩",
  small_file: "소형 파일",
};

export function QualityDetailPanel({
  selectedRow,
  detail,
  loading,
  error,
  stale,
  onRetry,
  onOpenRepair,
  onClose,
  className = "",
}: {
  selectedRow: QualityRow | null;
  detail: QualityIssueDetail | null;
  loading: boolean;
  error: string | null;
  stale: boolean;
  onRetry: () => void;
  onOpenRepair: () => void;
  onClose?: () => void;
  className?: string;
}) {
  const issueType = selectedRow?.issueType ?? detail?.issueType;

  return (
    <aside
      className={`flex h-full min-h-0 flex-col overflow-hidden bg-background ${className}`}
      data-testid="quality-detail-panel"
    >
      <div className="flex shrink-0 items-start justify-between gap-2 border-b border-outline p-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-wide text-muted">Quality issue detail</p>
          <h2 className="mt-1 text-lg font-bold text-on-surface">
            {issueType ? issueTypeLabels[issueType] : "선택 없음"}
          </h2>
          <p className="mt-2 truncate text-sm text-on-surface-variant">
            {selectedRow ? selectedRow.name : "왼쪽 grid에서 이슈 행을 선택하세요."}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            data-testid="quality-detail-panel-close"
            className="shrink-0 rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover"
            onClick={onClose}
          >
            닫기
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 text-sm">
        {loading && (
          <p className="text-muted" data-testid="quality-detail-loading">
            불러오는 중…
          </p>
        )}

        {error && !loading && (
          <div
            className="rounded-md border border-error/40 bg-error/10 p-4 text-error"
            data-testid="quality-detail-error"
          >
            <p>{error}</p>
            <button
              type="button"
              data-testid="quality-detail-retry"
              className="mt-3 rounded-md border border-outline px-3 py-1 text-xs font-semibold text-on-surface hover:bg-hover"
              onClick={onRetry}
            >
              Retry
            </button>
          </div>
        )}

        {stale && !loading && (
          <p
            className="mb-4 rounded-md border border-outline bg-surface-elevated p-3 text-warning"
            data-testid="quality-detail-stale"
            role="status"
          >
            라이브러리가 변경되었습니다. 목록을 새로고침하거나 행을 다시 선택하세요.
          </p>
        )}

        {detail && !error && !loading && (
          <dl className={`space-y-3 ${stale ? "opacity-60" : ""}`}>
            <div>
              <dt className="text-muted">Name</dt>
              <dd>{detail.name}</dd>
            </div>
            <div>
              <dt className="text-muted">Path</dt>
              <dd className="break-all">{detail.path}</dd>
            </div>
            <div>
              <dt className="text-muted">Encoding</dt>
              <dd>{detail.encoding}</dd>
            </div>
            <div>
              <dt className="text-muted">Severity</dt>
              <dd>{detail.severity}</dd>
            </div>
            <div>
              <dt className="text-muted">Evidence</dt>
              <dd>
                {detail.evidence.kind}: {detail.evidence.message}
              </dd>
            </div>
            <div>
              <dt className="text-muted">File size</dt>
              <dd>{detail.file.sizeBytes} bytes</dd>
            </div>
            <div>
              <dt className="text-muted">Repair</dt>
              <dd>{detail.repairEligibility.label}</dd>
            </div>
            {detail.repairEligibility.eligible && !stale && (
              <button
                type="button"
                data-testid="quality-repair-open"
                className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:bg-primary/90"
                onClick={onOpenRepair}
              >
                복구 미리보기
              </button>
            )}
            {import.meta.env.DEV && (
              <div>
                <dt className="text-muted">Raw (dev)</dt>
                <dd>
                  <pre className="mt-1 max-h-40 overflow-auto rounded bg-surface p-2 text-xs">
                    {JSON.stringify(detail, null, 2)}
                  </pre>
                </dd>
              </div>
            )}
          </dl>
        )}

        {!loading && !error && !detail && selectedRow && (
          <p className="text-muted" data-testid="quality-detail-empty">
            상세 정보를 불러올 수 없습니다.
          </p>
        )}

        {!loading && !error && !detail && !selectedRow && (
          <p className="text-muted">행을 선택하세요.</p>
        )}
      </div>
    </aside>
  );
}
