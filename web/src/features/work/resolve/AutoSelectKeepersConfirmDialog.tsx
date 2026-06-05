import { MAX_REVIEW_MUTATIONS } from "../../../constants/reviewBulk";
import type { AutoSelectKeepersStats } from "./autoSelectKeepers";

export function AutoSelectKeepersConfirmDialog({
  open,
  stats,
  onConfirm,
  onCancel,
  mutating,
}: {
  open: boolean;
  stats: AutoSelectKeepersStats;
  onConfirm: () => void;
  onCancel: () => void;
  mutating?: boolean;
}) {
  if (!open) return null;

  const capped = stats.unreviewedFileCount > MAX_REVIEW_MUTATIONS;

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
        <p className="mt-2 text-sm text-on-surface-variant">
          Exact {stats.exactUnreviewed.toLocaleString()} · Near{" "}
          {stats.nearUnreviewed.toLocaleString()} · Relation{" "}
          {stats.relationUnreviewed.toLocaleString()} 미검토 파일
        </p>
        <p className="mt-2 text-sm text-on-surface-variant">
          Keeper {stats.keeperCount.toLocaleString()} · 이동 후보{" "}
          {stats.moveCandidateCount.toLocaleString()}
        </p>
        <p className="mt-2 text-xs text-muted" data-testid="auto-select-keeper-rule">
          Keeper 규칙: 크기 → 수정 시각 → 경로 → 파일 ID
        </p>
        {capped && (
          <p
            className="mt-2 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-on-surface"
            data-testid="auto-select-cap-warning"
          >
            한 번에 최대 {MAX_REVIEW_MUTATIONS.toLocaleString()}건만 승인됩니다. 나머지는 필터를
            좁힌 뒤 다시 실행하세요.
          </p>
        )}
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
            disabled={mutating || stats.unreviewedFileCount === 0}
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
