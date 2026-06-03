/** Phases Python may emit; excludes legacy "scan" wire input. */
export type NormalizedPipelinePhase =
  | "idle"
  | "probe"
  | "persist"
  | "exact_index"
  | "analyze"
  | "finalize";

export function normalizePipelinePhase(phase: string): NormalizedPipelinePhase {
  if (phase === "scan") {
    return "probe";
  }
  return phase as NormalizedPipelinePhase;
}

export function pipelinePhaseLabel(
  phase: string,
  label: string,
  scan: { indexReady: boolean; state: string },
): string {
  const normalized = normalizePipelinePhase(phase);
  if (
    normalized === "probe" ||
    normalized === "persist" ||
    normalized === "exact_index" ||
    normalized === "analyze"
  ) {
    return label;
  }
  if (scan.indexReady && scan.state === "running") {
    return "파일 목록 준비됨";
  }
  return label;
}
