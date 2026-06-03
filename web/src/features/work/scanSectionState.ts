import type { PipelineSnapshot, ScanSnapshot } from "../../types/snapshot";

export type ScanSectionState = "empty" | "ready" | "running" | "success" | "error";

export function deriveScanSectionState(args: {
  folderPath: string | null;
  scan: ScanSnapshot;
  pipeline: PipelineSnapshot;
}): ScanSectionState {
  if (!args.folderPath?.trim()) {
    return "empty";
  }
  if (args.scan.state === "running") {
    return "running";
  }
  if (args.scan.state === "error") {
    return "error";
  }
  if (args.scan.state === "success") {
    return "success";
  }
  return "ready";
}
