import type { AutoSelectSummary } from "./computeAutoSelectSummary";

export function AutoSelectKeepersConfirmDialog({
  open,
  summary,
  onConfirm,
  onCancel,
  mutating,
}: {
  open: boolean;
  summary: AutoSelectSummary;
  onConfirm: () => void;
  onCancel: () => void;
  mutating?: boolean;
}) {
  if (!open) return null;

  const {
    unreviewedCount,
    keeperCount,
    moveCandidateCount,
    exactCount,
    nearCount,
    relationCount,
    capped,
    partialLoad,
    keeperPreviewUsesMtime,
    samples,
  } = summary;

  const hasSamples =
    samples &&
    (samples.keepers.length > 0 ||
      samples.moveCandidates.length > 0 ||
      samples.exact.length > 0 ||
      samples.near.length > 0 ||
      samples.relation.length > 0);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auto-select-keepers-confirm-title"
      data-testid="auto-select-keepers-confirm-dialog"
    >
      <div
        className="relative z-[101] w-full max-w-md rounded-md border border-outline bg-surface p-5 shadow-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <h2
          id="auto-select-keepers-confirm-title"
          className="text-lg font-bold text-on-surface"
        >
          미검토 전체 자동 선정
        </h2>

        <p className="mt-3 text-sm text-on-surface-variant">
          미검토 {unreviewedCount.toLocaleString()}건을 자동 선정합니다.
        </p>

        <div className="mt-3 text-sm text-on-surface-variant">
          <p className="font-semibold text-on-surface">보관 기준:</p>
          <ol className="mt-1 list-decimal pl-5">
            <li>가장 용량이 큰 파일</li>
            <li>용량이 같으면 가장 최근 수정된 파일</li>
          </ol>
        </div>

        <div className="mt-3 text-sm text-on-surface-variant">
          <p className="font-semibold text-on-surface">결과:</p>
          <ul className="mt-1 list-disc pl-5">
            <li data-testid="auto-select-summary-keepers">
              보관 {keeperCount.toLocaleString()}건
            </li>
            <li data-testid="auto-select-summary-move-candidates">
              이동 후보 {moveCandidateCount.toLocaleString()}건
            </li>
            <li data-testid="auto-select-summary-exact">
              Exact {exactCount.toLocaleString()}건
            </li>
            <li data-testid="auto-select-summary-near">
              Near {nearCount.toLocaleString()}건
            </li>
            <li data-testid="auto-select-summary-relation">
              Relation {relationCount.toLocaleString()}건
            </li>
          </ul>
        </div>

        {!keeperPreviewUsesMtime && (
          <p className="mt-2 text-xs text-muted" data-testid="auto-select-mtime-footnote">
            수정 시각이 로드되지 않아 보관 미리보기는 크기·경로 기준으로 표시됩니다.
          </p>
        )}

        {hasSamples && (
          <div className="mt-3 rounded-md border border-outline/60 bg-background/40 px-3 py-2 text-xs text-muted">
            {samples!.keepers.length > 0 && (
              <p>보관 예: {samples!.keepers.join(", ")}</p>
            )}
            {samples!.moveCandidates.length > 0 && (
              <p className="mt-1">이동 예: {samples!.moveCandidates.join(", ")}</p>
            )}
          </div>
        )}

        {partialLoad && (
          <p
            className="mt-2 text-xs text-warn"
            data-testid="batch-partial-load-warning"
          >
            일부만 로드됨 — 표시된 수치는 로드된 행 기준입니다.
          </p>
        )}

        {capped && (
          <p
            className="mt-2 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-on-surface"
            data-testid="bulk-auto-select-cap-warning"
          >
            현재 결과가 500건을 초과합니다. 이번 작업은 상위 500건만 처리하며, 나머지는 같은
            필터에서 다시 실행할 수 있습니다.
          </p>
        )}

        <p className="mt-3 text-sm text-on-surface-variant">
          확인 후 이동 계획 미리보기에서 최종 이동 대상을 검토합니다.
        </p>

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            data-testid="auto-select-keepers-confirm-cancel"
            disabled={mutating}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:opacity-50"
            onClick={onCancel}
          >
            취소
          </button>
          <button
            type="button"
            data-testid="auto-select-keepers-confirm-ok"
            disabled={mutating || unreviewedCount === 0}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onConfirm}
          >
            {mutating ? "처리 중…" : "자동 선정 및 승인"}
          </button>
        </div>
      </div>
    </div>
  );
}
