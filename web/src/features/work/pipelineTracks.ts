import type { PipelineSnapshot, ScanSnapshot } from "../../types/snapshot";
import { normalizePipelinePhase } from "./pipelinePhase";

export type PipelineTrackId = "foreground" | "background";

export type PipelineTrack = {
  id: PipelineTrackId;
  title: string;
  label: string;
  percent: number;
  visible: boolean;
  complete: boolean;
  /** Right-side status, e.g. `2/3` or `42%`. */
  statusText: string;
};

export type PipelineTracksModel = {
  tracks: PipelineTrack[];
  dual: boolean;
  cancellable: boolean;
};

const FOREGROUND_PHASES = new Set(["probe", "persist", "exact_index", "finalize"]);

function formatStepStatus(step: number, stepTotal: number, percent: number): string {
  if (stepTotal > 0) {
    return `${Math.min(step, stepTotal)}/${stepTotal}`;
  }
  return `${percent}%`;
}

/** Split pipeline UI into index (foreground) vs deep analysis (background) tracks. */
export function derivePipelineTracks(
  pipeline: PipelineSnapshot,
  scan: ScanSnapshot,
): PipelineTracksModel {
  const phase = normalizePipelinePhase(pipeline.phase);
  const foregroundBusy = FOREGROUND_PHASES.has(phase);
  const background = pipeline.background;

  const foreground: PipelineTrack = foregroundBusy
    ? {
        id: "foreground",
        title: "인덱스",
        label: pipeline.label,
        percent: pipeline.percent,
        visible: true,
        complete: false,
        statusText: `${pipeline.percent}%`,
      }
    : scan.indexReady || scan.state === "success"
      ? {
          id: "foreground",
          title: "인덱스",
          label: "준비 완료",
          percent: 100,
          visible: true,
          complete: true,
          statusText: "100%",
        }
      : {
          id: "foreground",
          title: "파이프라인",
          label: pipeline.label,
          percent: pipeline.percent,
          visible: true,
          complete: phase === "idle" && pipeline.percent >= 100,
          statusText: `${pipeline.percent}%`,
        };

  let backgroundTrack: PipelineTrack | null = null;
  if (background?.active) {
    backgroundTrack = {
      id: "background",
      title: "심층 분석",
      label: background.label,
      percent: background.percent,
      visible: true,
      complete: false,
      statusText: formatStepStatus(background.step, background.stepTotal, background.percent),
    };
  } else if (
    scan.indexReady &&
    !scan.deepAnalysisComplete &&
    scan.state === "success" &&
    phase === "analyze"
  ) {
    backgroundTrack = {
      id: "background",
      title: "심층 분석",
      label: pipeline.label,
      percent: pipeline.percent,
      visible: true,
      complete: false,
      statusText: `${pipeline.percent}%`,
    };
  }

  const tracks = backgroundTrack ? [foreground, backgroundTrack] : [foreground];

  return {
    tracks,
    dual: backgroundTrack !== null,
    cancellable: pipeline.cancellable && foregroundBusy,
  };
}
