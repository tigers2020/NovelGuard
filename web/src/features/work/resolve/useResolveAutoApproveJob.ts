import { useCallback, useEffect, useRef } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../../app/providers/snapshotHooks";
import type { ReviewRowsQuery } from "../../../types/review";
import type { ResolveAutoApproveJobSnapshot } from "../../../types/resolveAutoApproveJob";

function terminalJobKey(job: ResolveAutoApproveJobSnapshot): string | null {
  if (job.status !== "complete" && job.status !== "error" && job.status !== "cancelled") {
    return null;
  }
  return job.finishedAt ?? `${job.status}:${job.persistedRevision ?? "none"}`;
}

export function useResolveAutoApproveJob({
  onJobTerminal,
}: {
  onJobTerminal?: () => void | Promise<void>;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const job = useSnapshot().resolveAutoApproveJob;
  const lastHandledTerminalKeyRef = useRef<string | null>(null);
  const onJobTerminalRef = useRef(onJobTerminal);

  useEffect(() => {
    onJobTerminalRef.current = onJobTerminal;
  }, [onJobTerminal]);

  useEffect(() => {
    const key = terminalJobKey(job);
    if (!key || lastHandledTerminalKeyRef.current === key) {
      return;
    }
    lastHandledTerminalKeyRef.current = key;
    void (async () => {
      await refreshSnapshot();
      await onJobTerminalRef.current?.();
    })();
  }, [job, refreshSnapshot]);

  const startJob = useCallback(
    async (query: ReviewRowsQuery) => {
      await bridge.startResolveAutoApproveJob(query);
      await refreshSnapshot();
    },
    [bridge, refreshSnapshot],
  );

  const cancelJob = useCallback(async () => {
    await bridge.cancelResolveAutoApproveJob();
    await refreshSnapshot();
  }, [bridge, refreshSnapshot]);

  const isRunning = job.status === "running";

  return { job, isRunning, startJob, cancelJob };
}
