import {
  type SnapshotInvalidationEvent,
  isDebouncedInvalidationReason,
} from "../types/snapshotInvalidation";

export type InvalidationSchedulerOptions = {
  debounceMs: number;
  onRefresh: () => void | Promise<void>;
};

export function createInvalidationScheduler(options: InvalidationSchedulerOptions) {
  const { debounceMs, onRefresh } = options;
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let pendingSequence = 0;
  let refreshInFlight = false;
  let pendingRefresh = false;

  const runRefresh = () => {
    if (refreshInFlight) {
      pendingRefresh = true;
      return;
    }
    refreshInFlight = true;
    Promise.resolve(onRefresh()).finally(() => {
      refreshInFlight = false;
      if (pendingRefresh) {
        pendingRefresh = false;
        runRefresh();
      }
    });
  };

  const flushDebounce = (): boolean => {
    if (debounceTimer !== undefined) {
      clearTimeout(debounceTimer);
      debounceTimer = undefined;
    }
    if (pendingSequence > 0) {
      pendingSequence = 0;
      return true;
    }
    return false;
  };

  const scheduleDebounced = (sequence: number) => {
    pendingSequence = Math.max(pendingSequence, sequence);
    if (debounceTimer !== undefined) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = undefined;
      pendingSequence = 0;
      runRefresh();
    }, debounceMs);
  };

  return {
    handle(event: SnapshotInvalidationEvent) {
      if (isDebouncedInvalidationReason(event.reason)) {
        scheduleDebounced(event.sequence);
        return;
      }
      flushDebounce();
      runRefresh();
    },
    dispose() {
      if (debounceTimer !== undefined) {
        clearTimeout(debounceTimer);
      }
    },
  };
}
