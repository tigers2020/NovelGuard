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
  const isRunning = job.status === "running" || job.status === "queued";
  const lastHandledTerminalKeyRef = useRef<string | null>(null);
  const onJobTerminalRef = useRef(onJobTerminal);

  useEffect(() => {
    onJobTerminalRef.current = onJobTerminal;
  }, [onJobTerminal]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | undefined;

    const poll = async () => {
      if (cancelled) {
        return;
      }
      try {
        const latest = await bridge.getFinalizeJob();
        if (!cancelled) {
          await refreshSnapshot();
        }
        if (!isFinalizeJobTerminal(latest.status) && !cancelled) {
          timeoutId = window.setTimeout(() => void poll(), 1000);
        }
      } catch {
        if (!cancelled) {
          await refreshSnapshot();
          timeoutId = window.setTimeout(() => void poll(), 1000);
        }
      }
    };

    timeoutId = window.setTimeout(() => void poll(), 1000);

    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [bridge, refreshSnapshot, isRunning]);

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

  return { job, isRunning, startJob, cancelJob };
}
