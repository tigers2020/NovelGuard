import { BridgeCallError } from "./bridgeErrors";
import { getBridgeTimeoutMs } from "./bridgeTimeouts";
import { toBridgeCallError } from "./parseBridgeRejection";

export async function callBridge<T>(
  fn: () => Promise<T>,
  options: { method: string; timeoutMs?: number },
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? getBridgeTimeoutMs(options.method);
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
    throw toBridgeCallError(err, options.method);
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
}
