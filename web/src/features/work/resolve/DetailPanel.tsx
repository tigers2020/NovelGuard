import type {
  DuplicateGroupDetail,
  DuplicateGroupMemberDetail,
  ReviewRow,
} from "../../../types/review";
function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
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
}) {
  return (
    <aside
      className="h-full min-h-0 w-[360px] shrink-0 overflow-y-auto bg-background p-4"
      data-testid="detail-panel"
    >
      <div className="rounded-md border border-outline bg-surface p-4">
        <p className="text-xs uppercase tracking-wide text-muted">Evidence & Move Detail</p>
        <h2 className="mt-1 text-lg font-bold text-on-surface">
          {selectedRow?.type ?? "선택 없음"}
        </h2>
        <p className="mt-2 text-sm text-on-surface-variant">
          {selectedRow
            ? selectedRow.name
            : "왼쪽 grid에서 그룹 또는 파일을 선택하세요."}
        </p>
      </div>

      {loading && (
        <p className="mt-4 text-sm text-muted" data-testid="detail-loading">
          Loading group detail…
        </p>
      )}

      {error && !loading && (
        <div className="mt-4 rounded-md border border-error/40 bg-error/10 p-4 text-sm text-error">
          <p>{error}</p>
          <button
            type="button"
            className="mt-2 rounded-md border border-outline px-2 py-1 text-xs font-semibold text-on-surface"
            onClick={onRefreshDetail}
          >
            Retry
          </button>
        </div>
      )}

      {detail?.status === "not_found" && !loading && (
        <div
          className="mt-4 rounded-md border border-outline bg-surface p-4 text-sm text-on-surface-variant"
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
        <div className="mt-4 space-y-3">
          <div className="rounded-md border border-outline bg-surface p-4">
            <p className="text-sm font-semibold text-on-surface">Group</p>
            <p className="mt-1 text-sm text-on-surface-variant">
              <span data-testid="detail-member-count">{detail.members.length}</span> members ·{" "}
              {detail.groupStatus}
            </p>
          </div>

          <div className="rounded-md border border-outline bg-surface p-4">
            <p className="text-sm font-semibold text-on-surface">Keeper</p>
            <fieldset className="mt-2 space-y-2" disabled={mutating}>
              {detail.members.map((member) => (
                <label
                  key={member.fileId}
                  className="flex cursor-pointer items-start gap-2 text-sm text-on-surface"
                >
                  <input
                    type="radio"
                    name={`keeper-${detail.groupId}`}
                    checked={member.isKeeper}
                    aria-checked={member.isKeeper}
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
          </div>

          {detail.type === "exact" && "movePlan" in detail && (
            <div className="rounded-md border border-outline bg-surface p-4">
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
                    {member.status} · {formatBytes(member.sizeBytes)} · {member.encoding} ·{" "}
                    {member.integrity.label}
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
              {detail.type === "near" ? "Near duplicate" : detail.evidence.matchKind}
            </p>
            {detail.type === "near" ? (
              <>
                <p className="mt-1 text-sm text-on-surface">
                  Max similarity: {detail.evidence.maxSimilarity.toFixed(2)} (threshold{" "}
                  {detail.evidence.threshold})
                </p>
                <p className="mt-1 text-xs text-muted">{detail.evidence.comparisonMethod}</p>
              </>
            ) : (
              <p className="mt-1 break-all font-mono text-xs text-muted">
                {detail.evidence.contentSha256 || "—"}
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
    </aside>
  );
}
