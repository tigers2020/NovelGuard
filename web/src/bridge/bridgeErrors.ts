export type BridgeErrorCode = "timeout" | "rejected" | "missing_method";

export class BridgeCallError extends Error {
  readonly code: BridgeErrorCode;
  readonly method: string;

  constructor(message: string, options: { code: BridgeErrorCode; method: string; cause?: unknown }) {
    super(message);
    this.name = "BridgeCallError";
    this.code = options.code;
    this.method = options.method;
    if (options.cause instanceof Error) {
      this.cause = options.cause;
    }
  }
}
