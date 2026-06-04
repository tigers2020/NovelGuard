import type {
  DuplicateGroupDetail,
  DuplicateGroupMemberDetail,
  ReviewRow,
  ReviewRowType,
} from "../../../types/review";
import { reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function rowTypeBadgeClass(type: ReviewRowType | undefined): string {
  if (type === "near") return "bg-secondary/20 text-secondary";
  if (type === "relation") return "bg-primary/15 text-primary";
  if (type === "exact") return "bg-success/15 text-success";
  return "bg-surface text-muted";
}

export function DetailPanel({
  selectedRow,
  detail,
  loading,
  error,
  mutating,
  onSetKeeper,
  onMarkConflict,
  onReset,
  onRefreshDetail,
  onClose,
  className = "",
}: {
  selectedRow: ReviewRow | null;
  detail: DuplicateGroupDetail | null;
  loading: boolean;
  error: string | null;
  mutating: boolean;
  onSetKeeper: (member: DuplicateGroupMemberDetail) => void;
  onMarkConflict: () => void;
  onReset: () => void;
  onRefreshDetail: () => void;
  onClose?: () => void;
  className?: string;
}) {
  const rowType = selectedRow?.type;
  const keeperEditable =
    detail?.status === "ok" &&
    (detail.type === "exact" || detail.type === "near" || detail.type === "relation");

  return (
    <aside
      className={`flex h-full min-h-0 flex-col overflow-hidden bg-background ${className}`}
      data-testid="detail-panel"
    >
      <div className="flex shrink-0 items-start justify-between gap-2 border-b border-outline p-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-wide text-muted">Evidence & Move Detail</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2
              className="text-lg font-bold text-on-surface"
              data-testid={rowType ? `detail-row-type-${rowType}` : "detail-row-type-none"}
            >
              {rowType ? reviewTypeLabel[rowType] : "선택 없음"}
            </h2>
            {rowType && (
              <span
                className={`rounded-sm px-2 py-0.5 text-xs font-semibold ${rowTypeBadgeClass(rowType)}`}
              >
                {rowType}
              </span>
            )}
          </div>
          <p className="mt-2 truncate text-sm text-on-surface-variant">
            {selectedRow ? selectedRow.name : "목록에서 그룹 또는 파일을 선택하세요."}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            data-testid="detail-panel-close"
            className="shrink-0 rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface hover:bg-hover"
            onClick={onClose}
          >
            닫기
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {loading && (
          <p className="text-sm text-muted" data-testid="detail-loading">
            Loading group detail…
          </p>
        )}

        {error && !loading && (
          <div
            className="rounded-md border border-error/40 bg-error/10 p-4 text-sm text-error"
            data-testid="detail-error"
          >
            <p>{error}</p>
            <button
              type="button"
              data-testid="detail-retry"
              className="mt-2 rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface"
              onClick={onRefreshDetail}
            >
              Retry
            </button>
          </div>
        )}

        {detail?.status === "not_found" && !loading && (
          <div
            className="rounded-md border border-outline bg-surface p-4 text-sm text-on-surface-variant"
            data-testid="detail-not-found"
          >
            <p>그룹을 찾을 수 없습니다. 목록을 새로고침하세요.</p>
            <button
              type="button"
              className="mt-3 rounded-md border border-outline px-3 py-2 text-xs font-semibold text-on-surface hover:bg-hover"
              onClick={onRefreshDetail}
            >
              새로고침
            </button>
          </div>
        )}

        {detail?.status === "ok" && !loading && (
          <div className="space-y-3">
            <div className="rounded-md border border-outline bg-surface p-4">
              <p className="text-sm font-semibold text-on-surface">Group</p>
              <p className="mt-1 text-sm text-on-surface-variant">
                <span data-testid="detail-member-count">{detail.members.length}</span> members ·{" "}
                {reviewStatusLabel[detail.groupStatus]} ({detail.groupStatus})
              </p>
              <p className="mt-1 text-xs text-muted">
                Keeper: <span data-testid="detail-keeper-label">{detail.keeperLabel}</span>
              </p>
            </div>

            <div className="rounded-md border border-outline bg-surface p-4">
              <p className="text-sm font-semibold text-on-surface">Keeper</p>
              <fieldset className="mt-2 space-y-2" disabled={mutating || !keeperEditable}>
                {detail.members.map((member) => (
                  <label
                    key={member.fileId}
                    className={`flex items-start gap-2 text-sm ${
                      keeperEditable ? "cursor-pointer" : "cursor-not-allowed opacity-80"
                    } text-on-surface`}
                  >
                    <input
                      type="radio"
                      name={`keeper-${detail.groupId}`}
                      checked={member.isKeeper}
                      aria-checked={member.isKeeper}
                      disabled={!keeperEditable}
                      data-testid={`detail-keeper-radio-${member.fileId}`}
                      onChange={() => onSetKeeper(member)}
                    />
                    <span>
                      {member.name}
                      <span className="block text-xs text-muted">{member.path}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              {!keeperEditable && (
                <p className="mt-2 text-xs text-muted">
                  Keeper 변경은 Exact duplicate 그룹에서만 사용할 수 있습니다.
                </p>
              )}
            </div>

            {detail.type === "exact" && "movePlan" in detail && (
              <div
                className="rounded-md border border-outline bg-surface p-4"
                data-testid="detail-move-plan"
              >
                <p className="text-sm font-semibold text-on-surface">Move plan</p>
                <dl className="mt-2 space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted">Keeper</dt>
                    <dd className="font-medium text-on-surface">{detail.movePlan.keeperAction}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted">Duplicates</dt>
                    <dd className="font-medium text-on-surface">
                      {detail.movePlan.duplicateAction} → {detail.movePlan.targetFolder}
                    </dd>
                  </div>
                </dl>
              </div>
            )}

            <div className="rounded-md border border-outline bg-surface p-4">
              <p className="text-sm font-semibold text-on-surface">Members</p>
              <ul className="mt-2 space-y-2 text-sm">
                {detail.members.map((member) => (
                  <li
                    key={member.rowId}
                    className="border-b border-outline pb-2 last:border-0 last:pb-0"
                  >
                    <p className="font-medium text-on-surface">{member.name}</p>
                    <p className="text-xs text-muted">
                      {reviewStatusLabel[member.status]} · {formatBytes(member.sizeBytes)} ·{" "}
                      {member.encoding} · {member.integrity.label}
                    </p>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!selectedRow || mutating}
                data-testid="detail-mark-conflict"
                onClick={onMarkConflict}
                className="rounded-md border border-outline px-3 py-2 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                충돌 표시
              </button>
              <button
                type="button"
                disabled={!selectedRow || mutating}
                data-testid="detail-reset"
                onClick={onReset}
                className="rounded-md border border-outline px-3 py-2 text-xs font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                되돌리기
              </button>
            </div>

            <div className="rounded-md border border-outline bg-surface p-4">
              <p className="text-sm font-semibold text-on-surface">Evidence</p>
              <p className="mt-2 text-xs text-on-surface-variant">
                {detail.type === "near"
                  ? "Near duplicate"
                  : detail.type === "relation"
                    ? `Relation (${detail.evidence.relationKind})`
                    : detail.evidence.matchKind}
              </p>
              {detail.type === "near" ? (
                <>
                  <p className="mt-1 text-sm text-on-surface">
                    Max similarity: {detail.evidence.maxSimilarity.toFixed(2)} (threshold{" "}
                    {detail.evidence.threshold})
                  </p>
                  <p className="mt-1 text-xs text-muted">{detail.evidence.comparisonMethod}</p>
                </>
              ) : detail.type === "relation" ? (
                <>
                  <p className="mt-1 text-sm text-on-surface">
                    Confidence: {detail.evidence.confidenceLabel}
                  </p>
                  {detail.evidence.relationKind === "title_prefix_overlap" ? (
                    <p className="mt-1 text-xs text-on-surface-variant">
                      파일명이 같은 제목 접두를 공유합니다. 신뢰도 낮음 — 검토 전용이며 이동·적용은
                      Exact 그룹에서만 가능합니다.
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs text-muted">
                    Matched: {detail.evidence.matchedTokens.join(", ") || "—"}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Differs: {detail.evidence.differingTokens.join(", ") || "—"}
                  </p>
                </>
              ) : (
                <p className="mt-1 break-all font-mono text-xs text-muted">
                  {"contentSha256" in detail.evidence ? detail.evidence.contentSha256 || "—" : "—"}
                </p>
              )}
            </div>

            <details className="rounded-md border border-outline bg-surface p-4">
              <summary className="cursor-pointer text-sm font-semibold text-on-surface">
                Detail JSON
              </summary>
              <pre className="mt-3 overflow-x-auto rounded-md bg-background p-3 text-xs text-on-surface-variant">
                {JSON.stringify(detail, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </aside>
  );
}
