import type { AutoSelectKeepersSummary } from "../../../types/autoSelectSummary";
import { MAX_REVIEW_MUTATIONS, SELECTION_RESOLVE_ROW_CAP } from "../../../constants/reviewBulk";

export function AutoSelectConfirmDialog({
  open,
  summary,
  filteredCount,
  onConfirm,
  onCancel,
  mutating,
}: {
  open: boolean;
  summary: AutoSelectKeepersSummary | null;
  filteredCount: number;
  onConfirm: () => void;
  onCancel: () => void;
  mutating?: boolean;
}) {
  if (!open || summary === null) return null;

  const targetCount = summary.targetCount;
  const capped = filteredCount > MAX_REVIEW_MUTATIONS;
  const chunked = targetCount > SELECTION_RESOLVE_ROW_CAP;
  const chunkBatches = Math.ceil(targetCount / SELECTION_RESOLVE_ROW_CAP);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auto-select-confirm-title"
      data-testid="auto-select-confirm-dialog"
    >
      <div
        className="relative z-[101] w-full max-w-md rounded-md border border-outline bg-surface p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="auto-select-confirm-title" className="text-lg font-bold text-on-surface">
          미검토 자동 선정
        </h2>
        <p className="mt-3 whitespace-pre-line text-sm text-on-surface-variant">
          {`미검토 ${targetCount.toLocaleString()}건을 자동 선정합니다.

보관 기준:
1. 가장 용량이 큰 파일
2. 용량이 같으면 가장 최근 수정된 파일

결과:
- 보관 ${summary.keeperCount.toLocaleString()}건
- 이동 후보 ${summary.moveCandidateCount.toLocaleString()}건
- Exact ${summary.exactCount.toLocaleString()}건 / Near ${summary.nearCount.toLocaleString()}건 / Relation ${summary.relationCount.toLocaleString()}건

확인 후 이동 계획 미리보기에서 최종 이동 대상을 검토합니다.`}
        </p>
        {capped && (
          <p
            className="mt-2 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-on-surface"
            data-testid="auto-select-cap-warning"
          >
            한 번에 최대 {MAX_REVIEW_MUTATIONS.toLocaleString()}건만 처리됩니다. 나머지는 필터를
            좁힌 뒤 다시 실행하세요.
          </p>
        )}
        {chunked && (
          <p className="mt-2 text-xs text-muted">
            서버 제한으로 {chunkBatches}회에 나누어 처리합니다(회당 최대{" "}
            {SELECTION_RESOLVE_ROW_CAP.toLocaleString()}건).
          </p>
        )}
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            data-testid="auto-select-confirm-cancel"
            disabled={mutating}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:opacity-50"
            onClick={onCancel}
          >
            취소
          </button>
          <button
            type="button"
            data-testid="auto-select-confirm-ok"
            disabled={mutating || targetCount === 0}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onConfirm}
          >
            {mutating ? "처리 중…" : `${targetCount.toLocaleString()}건 선정·승인`}
          </button>
        </div>
      </div>
    </div>
  );
}
