import type { ResolveAutoApproveJobSnapshot } from "../../../types/resolveAutoApproveJob";
import {
  resolveAutoApprovePhaseLabel,
  resolveAutoApproveStatusLabel,
} from "./resolveAutoApproveJobCopy";

export function ResolveAutoApproveJobProgress({
  job,
  onCancel,
}: {
  job: ResolveAutoApproveJobSnapshot;
  onCancel?: () => void;
}) {
  if (job.status === "idle") {
    return null;
  }

  const phaseLabel = resolveAutoApprovePhaseLabel(job.phase);
  const showProgress = job.status === "running" || job.totalRows > 0;
  const showCancel = job.status === "running" && onCancel;

  return (
    <div
      className="border-b border-outline bg-surface px-4 py-2"
      data-testid="resolve-auto-approve-job-progress"
      role="status"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-on-surface" data-testid="resolve-auto-approve-status">
            {resolveAutoApproveStatusLabel(job.status)}
          </p>
          {phaseLabel && (
            <p className="text-xs text-muted" data-testid="resolve-auto-approve-phase">
              {phaseLabel}
            </p>
          )}
          {job.label && job.status === "running" && (
            <p className="text-xs text-on-surface-variant">{job.label}</p>
          )}
          {showProgress && (
            <p className="mt-1 text-xs text-on-surface-variant" data-testid="resolve-auto-approve-row-progress">
              {job.processedRows.toLocaleString()} / {job.totalRows.toLocaleString()} rows
            </p>
          )}
          {job.status === "running" && (
            <p className="mt-1 text-xs text-muted" data-testid="resolve-auto-approve-counts">
              scanned {job.scannedCount.toLocaleString()} · eligible {job.eligibleCount.toLocaleString()} ·
              keepers {job.keeperSetCount.toLocaleString()} · approved {job.approvedRowCount.toLocaleString()}
            </p>
          )}
          {job.status === "error" && job.error && (
            <p className="mt-1 text-xs text-error" data-testid="resolve-auto-approve-error">
              {job.error}
            </p>
          )}
        </div>
        {showCancel && (
          <button
            type="button"
            data-testid="resolve-auto-approve-cancel"
            onClick={onCancel}
            className="shrink-0 rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
          >
            취소
          </button>
        )}
      </div>
    </div>
  );
}
