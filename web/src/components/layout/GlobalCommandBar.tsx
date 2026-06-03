import type { PipelineSnapshot, ScanSnapshot } from "../../types/snapshot";
import {
  derivePipelineTracks,
  type PipelineTrack,
} from "../../features/work/pipelineTracks";

function PipelineTrackBar({ track, compact }: { track: PipelineTrack; compact: boolean }) {
  const barHeight = compact ? "h-1.5" : "h-2";

  return (
    <div
      data-testid={`global-command-bar-track-${track.id}`}
      data-state={track.complete ? "complete" : "active"}
      className={track.visible ? undefined : "hidden"}
    >
      <div className="flex items-center justify-between gap-3 text-sm">
        <span
          className={
            track.complete
              ? "font-medium text-on-surface-variant"
              : "font-semibold text-on-surface"
          }
        >
          {track.title} · {track.label}
        </span>
        <span className="text-xs tabular-nums text-muted">{track.statusText}</span>
      </div>
      <div
        className={`mt-1 overflow-hidden rounded-full bg-outline ${barHeight}`}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={track.percent}
        aria-label={`${track.title} ${track.label}`}
      >
        <div
          className={`${barHeight} rounded-full transition-all ${
            track.complete ? "bg-primary/45" : "bg-primary"
          }`}
          style={{ width: `${Math.max(0, Math.min(100, track.percent))}%` }}
        />
      </div>
    </div>
  );
}

export function GlobalCommandBar({
  pipeline,
  scan,
  onFullPipeline,
  onCancel,
}: {
  pipeline: PipelineSnapshot;
  scan: ScanSnapshot;
  onFullPipeline: () => void;
  onCancel: () => void;
}) {
  const { tracks, dual, cancellable } = derivePipelineTracks(pipeline, scan);
  const backgroundLabel = pipeline.background?.active ? pipeline.background.label : null;

  return (
    <footer
      className="shrink-0 border-t border-outline bg-surface px-5 py-3"
      data-testid="global-command-bar"
      data-dual={dual ? "true" : "false"}
    >
      <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
        <div className={dual ? "space-y-2" : undefined}>
          {tracks.map((track) => (
            <PipelineTrackBar key={track.id} track={track} compact={dual} />
          ))}
        </div>
        <div className="flex items-center gap-2">
          {cancellable ? (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md border border-error/40 bg-error/20 px-3 py-2 text-sm font-semibold text-error hover:bg-error/30"
            >
              중지
            </button>
          ) : backgroundLabel ? (
            <span
              className="max-w-[12rem] truncate rounded-md border border-outline px-3 py-2 text-xs font-semibold text-on-surface-variant"
              data-testid="global-command-bar-background-hint"
              title={backgroundLabel}
            >
              {backgroundLabel}
            </span>
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
