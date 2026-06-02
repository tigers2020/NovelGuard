export type SnapshotInvalidationReason =
  | "libraryRevision"
  | "pipelinePhase"
  | "scanProgress"
  | "applyComplete"
  | "repairComplete"
  | "finalizeComplete";

export type SnapshotInvalidationEvent = {
  type: "snapshotInvalidated";
  reason: SnapshotInvalidationReason;
  libraryRevision?: number;
  pipelinePhase?: string;
  sequence: number;
};

export const DEBOUNCED_INVALIDATION_REASONS: ReadonlySet<SnapshotInvalidationReason> = new Set([
  "scanProgress",
  "pipelinePhase",
]);

export function isDebouncedInvalidationReason(reason: SnapshotInvalidationReason): boolean {
  return DEBOUNCED_INVALIDATION_REASONS.has(reason);
}
