import { useCallback, useRef, useState } from "react";
import { BridgeCallError } from "../../bridge/bridgeErrors";

export const DEGRADED_BRIDGE_RETRY_DELAYS_MS = [1000, 3000, 5000] as const;

export function isBridgeTimeoutError(err: unknown): boolean {
  return err instanceof BridgeCallError && err.code === "timeout";
}

export type DegradedBridgeRetrySuccess<T> = {
  ok: true;
  value: T;
  attempts: number;
};

export type DegradedBridgeRetryTimeout = {
  ok: false;
  timedOut: true;
  attempts: number;
};

export type DegradedBridgeRetryFailure = {
  ok: false;
  timedOut: false;
  error: unknown;
  attempts: number;
};

export type DegradedBridgeRetryResult<T> =
  | DegradedBridgeRetrySuccess<T>
  | DegradedBridgeRetryTimeout
  | DegradedBridgeRetryFailure;

export async function withDegradedBridgeRetry<T>(
  fetcher: () => Promise<T>,
): Promise<DegradedBridgeRetryResult<T>> {
  for (let attempt = 0; attempt <= DEGRADED_BRIDGE_RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      const value = await fetcher();
      return { ok: true, value, attempts: attempt };
    } catch (err) {
      if (!isBridgeTimeoutError(err)) {
        return { ok: false, timedOut: false, error: err, attempts: attempt };
      }
      if (attempt >= DEGRADED_BRIDGE_RETRY_DELAYS_MS.length) {
        return { ok: false, timedOut: true, attempts: attempt + 1 };
      }
      await new Promise((r) => setTimeout(r, DEGRADED_BRIDGE_RETRY_DELAYS_MS[attempt]));
    }
  }
  return { ok: false, timedOut: true, attempts: DEGRADED_BRIDGE_RETRY_DELAYS_MS.length + 1 };
}

export type DegradedQueryState<T> = {
  data: T | null;
  loading: boolean;
  degraded: boolean;
  retryCount: number;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useDegradedBridgeQuery<T>(
  fetcher: () => Promise<T>,
  options: { isExpectedSlow?: boolean } = {},
): DegradedQueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [degraded, setDegraded] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const seqRef = useRef(0);

  const run = useCallback(async () => {
    const seq = ++seqRef.current;
    setLoading(true);
    setError(null);
    const result = await withDegradedBridgeRetry(fetcher);
    if (seq !== seqRef.current) return;

    if (result.ok) {
      setData(result.value);
      setDegraded(false);
      setRetryCount(result.attempts);
      setLoading(false);
      return;
    }

    if (result.timedOut) {
      setDegraded(true);
      setRetryCount(result.attempts);
      setError(null);
      setLoading(false);
      return;
    }

    setError(result.error instanceof Error ? result.error.message : "Query failed");
    setDegraded(false);
    setLoading(false);
  }, [fetcher]);

  return {
    data,
    loading,
    degraded: degraded || Boolean(options.isExpectedSlow),
    retryCount,
    error,
    refresh: run,
  };
}
