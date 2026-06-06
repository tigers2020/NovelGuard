import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { useDegradedBridgeQuery, withDegradedBridgeRetry } from "./useDegradedBridgeQuery";

afterEach(() => {
  vi.useRealTimers();
});

describe("withDegradedBridgeRetry", () => {
  it("returns value on first success", async () => {
    const fetcher = vi.fn().mockResolvedValue({ rows: [1] });
    await expect(withDegradedBridgeRetry(fetcher)).resolves.toEqual({
      ok: true,
      value: { rows: [1] },
      attempts: 0,
    });
  });
});

describe("useDegradedBridgeQuery", () => {
  it("preserves prior data after timeout and marks degraded", async () => {
    vi.useFakeTimers();
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ rows: ["a"] })
      .mockRejectedValue(
        new BridgeCallError("timeout", { code: "timeout", method: "query_file_rows" }),
      );

    const { result } = renderHook(() => useDegradedBridgeQuery(fetcher));

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.data).toEqual({ rows: ["a"] });
    expect(result.current.degraded).toBe(false);

    await act(async () => {
      const refreshPromise = result.current.refresh();
      await vi.runAllTimersAsync();
      await refreshPromise;
    });

    expect(result.current.data).toEqual({ rows: ["a"] });
    expect(result.current.degraded).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("retries timeouts with backoff then stops without hard error", async () => {
    vi.useFakeTimers();
    const fetcher = vi
      .fn()
      .mockRejectedValue(
        new BridgeCallError("timeout", { code: "timeout", method: "query_file_rows" }),
      );

    const { result } = renderHook(() => useDegradedBridgeQuery(fetcher));

    await act(async () => {
      void result.current.refresh();
      await vi.advanceTimersByTimeAsync(9_000);
    });

    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(result.current.degraded).toBe(true);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("surfaces non-timeout errors immediately", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useDegradedBridgeQuery(fetcher));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.error).toBe("boom");
    expect(result.current.degraded).toBe(false);
  });
});
