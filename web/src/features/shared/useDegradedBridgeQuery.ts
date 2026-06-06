import { useCallback, useRef, useState } from "react";
import { BridgeCallError } from "../../bridge/bridgeErrors";

const RETRY_DELAYS_MS = [1000, 3000, 5000] as const;

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
    for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt += 1) {
      try {
        const result = await fetcher();
        if (seq !== seqRef.current) return;
        setData(result);
        setDegraded(false);
        setRetryCount(attempt);
        setLoading(false);
        return;
      } catch (err) {
        if (seq !== seqRef.current) return;
        const isTimeout = err instanceof BridgeCallError && err.code === "timeout";
        if (!isTimeout) {
          setError(err instanceof Error ? err.message : "Query failed");
          setLoading(false);
          return;
        }
        setDegraded(true);
        setRetryCount(attempt + 1);
        if (attempt >= RETRY_DELAYS_MS.length) {
          setError(null);
          setLoading(false);
          return;
        }
        await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
      }
    }
    if (seq === seqRef.current) {
      setLoading(false);
    }
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
