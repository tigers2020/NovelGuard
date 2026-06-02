import type { ApplyFailedDetails, PreviewApplyErrorCode } from "../types/movePreview";
import type { RepairApplyErrorCode, RepairPreviewErrorCode } from "../types/qualityRepair";

export type QualityQueryErrorCode = "INVALID_SORT_FIELD";

export type FileRowQueryErrorCode = "INVALID_SORT_FIELD" | "INVALID_FILTER_VALUE";

export type BridgeErrorCode = "timeout" | "rejected" | "missing_method";

export const BRIDGE_ERROR_CODES = {
  productionUnavailable: "PRODUCTION_BRIDGE_UNAVAILABLE",
  devUnavailable: "DEV_BRIDGE_UNAVAILABLE",
} as const;

export class BridgeUnavailableError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "BridgeUnavailableError";
    this.code = code;
  }
}

export function getBridgeErrorCode(error: unknown): string {
  if (error instanceof BridgeUnavailableError) {
    return error.code;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "BRIDGE_UNAVAILABLE";
}

export class BridgeCallError extends Error {
  readonly code: BridgeErrorCode;
  readonly method: string;
  readonly reason?:
    | PreviewApplyErrorCode
    | RepairApplyErrorCode
    | RepairPreviewErrorCode
    | QualityQueryErrorCode
    | FileRowQueryErrorCode;
  readonly details?: ApplyFailedDetails;

  constructor(
    message: string,
    options: {
      code: BridgeErrorCode;
      method: string;
      reason?:
        | PreviewApplyErrorCode
        | RepairApplyErrorCode
        | RepairPreviewErrorCode
        | QualityQueryErrorCode
    | FileRowQueryErrorCode;
      details?: ApplyFailedDetails;
      cause?: unknown;
    },
  ) {
    super(message);
    this.name = "BridgeCallError";
    this.code = options.code;
    this.method = options.method;
    this.reason = options.reason;
    this.details = options.details;
    if (options.cause instanceof Error) {
      this.cause = options.cause;
    }
  }
}
