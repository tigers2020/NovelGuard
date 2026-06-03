import {
  MAX_REVIEW_MUTATIONS,
  SELECTION_RESOLVE_ROW_CAP,
  bulkMutationTargetCount,
} from "../../../constants/reviewBulk";

export function BulkFilterConfirmDialog({
  open,
  command,
  filteredCount,
  onConfirm,
  onCancel,
  mutating,
}: {
  open: boolean;
  command: "approve" | "exclude";
  filteredCount: number;
  onConfirm: () => void;
  onCancel: () => void;
  mutating?: boolean;
}) {
  if (!open) return null;

  const targetCount = bulkMutationTargetCount(filteredCount);
  const capped = filteredCount > MAX_REVIEW_MUTATIONS;
  const chunked = targetCount > SELECTION_RESOLVE_ROW_CAP;
  const verb = command === "approve" ? "승인" : "제외";
  const chunkBatches = Math.ceil(targetCount / SELECTION_RESOLVE_ROW_CAP);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bulk-filter-confirm-title"
      data-testid="bulk-filter-confirm-dialog"
    >
      <div
        className="relative z-[101] w-full max-w-md rounded-md border border-outline bg-surface p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="bulk-filter-confirm-title"
          className="text-lg font-bold text-on-surface"
        >
          필터 전체 {verb}
        </h2>
        <p className="mt-2 text-sm text-on-surface-variant">
          현재 필터·정렬·보기 모드에 맞는{" "}
          <span className="font-semibold text-on-surface">
            {filteredCount.toLocaleString()}
          </span>
          건 중{" "}
          <span className="font-semibold text-on-surface">
            {targetCount.toLocaleString()}
          </span>
          건을 {verb}합니다.
        </p>
        {capped && (
          <p
            className="mt-2 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-on-surface"
            data-testid="bulk-filter-cap-warning"
          >
            한 번에 최대 {MAX_REVIEW_MUTATIONS.toLocaleString()}건만 처리됩니다. 나머지는
            필터를 좁힌 뒤 다시 실행하세요.
          </p>
        )}
        {chunked && (
          <p className="mt-2 text-xs text-muted">
            서버 제한으로 {chunkBatches}회에 나누어 처리합니다(회당 최대{" "}
            {SELECTION_RESOLVE_ROW_CAP.toLocaleString()}건).
          </p>
        )}
        <p className="mt-3 text-xs text-muted">
          그룹 헤더만 선택한 경우와 같이, 그룹 단위 명령은 그룹 전체에 적용됩니다.
        </p>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            data-testid="bulk-filter-confirm-cancel"
            disabled={mutating}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:opacity-50"
            onClick={onCancel}
          >
            취소
          </button>
          <button
            type="button"
            data-testid="bulk-filter-confirm-ok"
            disabled={mutating || targetCount === 0}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={onConfirm}
          >
            {mutating ? "처리 중…" : `${targetCount.toLocaleString()}건 ${verb}`}
          </button>
        </div>
      </div>
    </div>
  );
}
