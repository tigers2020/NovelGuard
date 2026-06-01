import type { PreviewApplyErrorCode } from "../types/movePreview";

export type BridgeErrorCode = "timeout" | "rejected" | "missing_method";

export class BridgeCallError extends Error {
  readonly code: BridgeErrorCode;
  readonly method: string;
  readonly reason?: PreviewApplyErrorCode;

  constructor(
    message: string,
    options: {
      code: BridgeErrorCode;
      method: string;
      reason?: PreviewApplyErrorCode;
      cause?: unknown;
    },
  ) {
    super(message);
    this.name = "BridgeCallError";
    this.code = options.code;
    this.method = options.method;
    this.reason = options.reason;
    if (options.cause instanceof Error) {
      this.cause = options.cause;
    }
  }
}
