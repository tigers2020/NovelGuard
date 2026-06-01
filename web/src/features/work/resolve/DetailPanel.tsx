import type { ReviewRow } from "../../../types/review";

export function DetailPanel({ selectedRow }: { selectedRow: ReviewRow | null }) {
  return (
    <aside className="h-full min-h-0 w-[360px] shrink-0 overflow-y-auto bg-background p-4">
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

      {selectedRow && (
        <div className="mt-4 space-y-3">
          <div className="rounded-md border border-outline bg-surface p-4">
            <p className="text-sm font-semibold text-on-surface">Keeper decision</p>
            <p className="mt-2 text-sm text-on-surface-variant">{selectedRow.keeperLabel}</p>
          </div>
          <div className="rounded-md border border-outline bg-surface p-4">
            <p className="text-sm font-semibold text-on-surface">Move plan</p>
            <dl className="mt-2 space-y-2 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Action</dt>
                <dd className="font-medium text-on-surface">{selectedRow.proposedAction}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Target</dt>
                <dd className="font-medium text-on-surface">{selectedRow.targetFolder}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Encoding</dt>
                <dd className="font-medium text-on-surface">{selectedRow.encoding}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Integrity</dt>
                <dd className="font-medium text-on-surface">{selectedRow.integrity}</dd>
              </div>
            </dl>
          </div>
          <details className="rounded-md border border-outline bg-surface p-4">
            <summary className="cursor-pointer text-sm font-semibold text-on-surface">
              Decision JSON
            </summary>
            <pre className="mt-3 overflow-x-auto rounded-md bg-background p-3 text-xs text-on-surface-variant">
              {JSON.stringify(selectedRow, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </aside>
  );
}
