import type { FinalizeResult } from "./finalize";

export type FinalizeJobStatus =
  | "idle"
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type FinalizeJobSnapshot = {
  jobId: string | null;
  status: FinalizeJobStatus;
  progress: number;
  message: string;
  startedAt: string | null;
  finishedAt: string | null;
  result: FinalizeResult | null;
  error: string | null;
};

export const idleFinalizeJobSnapshot = (): FinalizeJobSnapshot => ({
  jobId: null,
  status: "idle",
  progress: 0,
  message: "",
  startedAt: null,
  finishedAt: null,
  result: null,
  error: null,
});

export function isFinalizeJobTerminal(status: FinalizeJobStatus): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}
