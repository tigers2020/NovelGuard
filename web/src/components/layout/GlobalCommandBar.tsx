import type { PipelineSnapshot } from "../../types/snapshot";

export function GlobalCommandBar({
  pipeline,
  onFullPipeline,
  onCancel,
}: {
  pipeline: PipelineSnapshot;
  onFullPipeline: () => void;
  onCancel: () => void;
}) {
  const running = pipeline.cancellable || pipeline.phase !== "idle";

  return (
    <footer className="shrink-0 border-t border-outline bg-surface px-5 py-3">
      <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-semibold text-on-surface">GlobalCommandBar · {pipeline.label}</span>
            <span className="text-xs tabular-nums text-muted">{pipeline.percent}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-outline" role="progressbar" aria-valuenow={pipeline.percent} aria-valuemin={0} aria-valuemax={100}>
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${pipeline.percent}%` }}
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          {running ? (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md border border-error/40 bg-error/20 px-3 py-2 text-sm font-semibold text-error hover:bg-error/30"
            >
              중지
            </button>
          ) : (
            <button
              type="button"
              onClick={onFullPipeline}
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90"
            >
              전체 실행
            </button>
          )}
        </div>
      </div>
    </footer>
  );
}
