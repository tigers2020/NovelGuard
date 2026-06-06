import type { ResolveAutoApproveSummary } from "./resolveAutoApproveSummary";

export type ResolveAutoApproveJobStatus =
  | "idle"
  | "running"
  | "complete"
  | "error"
  | "cancelled";

export type ResolveAutoApproveJobPhase =
  | "idle"
  | "summarize"
  | "set_keeper"
  | "approve"
  | "persist";

export type ResolveAutoApproveJobSnapshot = {
  status: ResolveAutoApproveJobStatus;
  phase: ResolveAutoApproveJobPhase;
  processedRows: number;
  totalRows: number;
  keeperCount: number;
  moveCandidateCount: number;
  scannedCount: number;
  eligibleCount: number;
  skippedConflictCount: number;
  skippedExcludedCount: number;
  label: string;
  error: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  summary: ResolveAutoApproveSummary | null;
};

export const idleResolveAutoApproveJobSnapshot = (): ResolveAutoApproveJobSnapshot => ({
  status: "idle",
  phase: "idle",
  processedRows: 0,
  totalRows: 0,
  keeperCount: 0,
  moveCandidateCount: 0,
  scannedCount: 0,
  eligibleCount: 0,
  skippedConflictCount: 0,
  skippedExcludedCount: 0,
  label: "",
  error: null,
  startedAt: null,
  finishedAt: null,
  summary: null,
});
