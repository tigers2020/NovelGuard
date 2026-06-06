import type { ResolveAutoApproveSummary } from "../../../types/resolveAutoApproveSummary";

export function AutoSelectKeepersConfirmDialog({
  open,
  summary,
  onConfirm,
  onCancel,
  mutating,
}: {
  open: boolean;
  summary: ResolveAutoApproveSummary;
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
    samples,
  } = summary;

  const hasSamples =
    samples.keepers.length > 0 ||
    samples.moveCandidates.length > 0 ||
    samples.exact.length > 0 ||
    samples.near.length > 0 ||
    samples.relation.length > 0;

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

        {hasSamples && (
          <div className="mt-3 rounded-md border border-outline/60 bg-background/40 px-3 py-2 text-xs text-muted">
            {samples.keepers.length > 0 && <p>보관 예: {samples.keepers.join(", ")}</p>}
            {samples.moveCandidates.length > 0 && (
              <p className="mt-1">이동 예: {samples.moveCandidates.join(", ")}</p>
            )}
          </div>
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
