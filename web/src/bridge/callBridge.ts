import { BridgeCallError } from "./bridgeErrors";

export async function callBridge<T>(
  fn: () => Promise<T>,
  options: { method: string; timeoutMs?: number },
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? 8_000;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () =>
        reject(
          new BridgeCallError(`Bridge call timed out: ${options.method}`, {
            code: "timeout",
            method: options.method,
          }),
        ),
      timeoutMs,
    );
  });

  try {
    return await Promise.race([fn(), timeoutPromise]);
  } catch (err) {
    if (err instanceof BridgeCallError) {
      throw err;
    }
    throw new BridgeCallError(`Bridge call failed: ${options.method}`, {
      code: "rejected",
      method: options.method,
      cause: err,
    });
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
}
