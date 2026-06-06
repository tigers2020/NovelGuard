import { useCallback, useEffect, useRef } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../../app/providers/snapshotHooks";
import type { RunFinalizeRequest } from "../../../types/finalize";
import {
  type FinalizeJobSnapshot,
  isFinalizeJobTerminal,
} from "../../../types/finalizeJob";

function terminalJobKey(job: FinalizeJobSnapshot): string | null {
  if (!isFinalizeJobTerminal(job.status)) {
    return null;
  }
  return job.finishedAt ?? `${job.status}:${job.jobId ?? "none"}`;
}

export function useFinalizeJob({
  onJobTerminal,
}: {
  onJobTerminal?: (job: FinalizeJobSnapshot) => void | Promise<void>;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const job = useSnapshot().finalizeJob;
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
      await onJobTerminalRef.current?.(job);
    })();
  }, [job, refreshSnapshot]);

  const startJob = useCallback(
    async (request: RunFinalizeRequest) => {
      const snapshot = await bridge.startFinalizeJob(request);
      await refreshSnapshot();
      return snapshot;
    },
    [bridge, refreshSnapshot],
  );

  const cancelJob = useCallback(async () => {
    await bridge.cancelFinalize();
    await refreshSnapshot();
  }, [bridge, refreshSnapshot]);

  const isRunning = job.status === "running" || job.status === "queued";

  return { job, isRunning, startJob, cancelJob };
}
