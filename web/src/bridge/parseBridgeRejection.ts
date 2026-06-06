import type { ApplyFailedDetails, PreviewApplyErrorCode } from "../types/movePreview";
import type { RepairApplyErrorCode, RepairPreviewErrorCode } from "../types/qualityRepair";
import type { RecoveryUndoReason } from "../types/recoveryUndo";
import { isRecoveryUndoReason } from "../types/recoveryUndo";
import {
  BridgeCallError,
  type FileRowQueryErrorCode,
  type QualityQueryErrorCode,
} from "./bridgeErrors";

const PREVIEW_APPLY_CODES: readonly PreviewApplyErrorCode[] = [
  "MISSING_PREVIEW_TOKEN",
  "INVALID_PREVIEW_TOKEN",
  "NO_PENDING_APPLY",
  "STALE_PREVIEW",
  "DESTINATION_EXISTS",
  "SELECTION_CHANGED",
  "APPLY_FAILED",
  "LIBRARY_BUSY",
  "INVALID_REVIEW_COMMAND",
  "INVALID_SETTING_VALUE",
  "REPAIR_PREVIEW_ACTIVE",
  "NEAR_DUPLICATE_APPLY_UNSUPPORTED",
  "RELATION_APPLY_UNSUPPORTED",
];

const REPAIR_PREVIEW_CODES: readonly RepairPreviewErrorCode[] = [
  "BATCH_LIMIT_EXCEEDED",
  "EMPTY_SELECTION",
  "MIXED_OR_INELIGIBLE_SELECTION",
  "MOVE_PREVIEW_ACTIVE",
  "REPAIR_PREVIEW_ACTIVE",
  "LIBRARY_BUSY",
];

const REPAIR_APPLY_CODES: readonly RepairApplyErrorCode[] = [
  "STALE_REPAIR_PREVIEW",
  "ISSUE_SELECTION_CHANGED",
  "PLAN_MISMATCH",
  "NO_PENDING_REPAIR",
  "MISSING_REPAIR_PREVIEW_TOKEN",
  "INVALID_REPAIR_PREVIEW_TOKEN",
  "REPAIR_FAILED",
  "LIBRARY_BUSY",
  "MOVE_PREVIEW_ACTIVE",
];

const FINALIZE_BRIDGE_CODES = [
  "NO_LIBRARY",
  "LIBRARY_BUSY",
  "FINALIZE_NOT_CONFIGURED",
  "INVALID_REQUEST",
  "REPORT_NOT_FOUND",
] as const;

type FinalizeBridgeErrorCode = (typeof FINALIZE_BRIDGE_CODES)[number];

type BridgeRejectionReason =
  | PreviewApplyErrorCode
  | RepairPreviewErrorCode
  | RepairApplyErrorCode
  | QualityQueryErrorCode
  | FileRowQueryErrorCode
  | FinalizeBridgeErrorCode
  | RecoveryUndoReason;

function isPreviewApplyCode(value: string): value is PreviewApplyErrorCode {
  return (PREVIEW_APPLY_CODES as readonly string[]).includes(value);
}

function isRepairPreviewCode(value: string): value is RepairPreviewErrorCode {
  return (REPAIR_PREVIEW_CODES as readonly string[]).includes(value);
}

function isRepairApplyCode(value: string): value is RepairApplyErrorCode {
  return (REPAIR_APPLY_CODES as readonly string[]).includes(value);
}

function isQualityQueryCode(value: string): value is QualityQueryErrorCode {
  return value === "INVALID_SORT_FIELD";
}

function isFileRowQueryCode(value: string): value is FileRowQueryErrorCode {
  return value === "INVALID_SORT_FIELD" || value === "INVALID_FILTER_VALUE";
}

function isFinalizeBridgeCode(value: string): value is FinalizeBridgeErrorCode {
  return (FINALIZE_BRIDGE_CODES as readonly string[]).includes(value);
}

function isBridgeRejectionReason(value: string): value is BridgeRejectionReason {
  return (
    isPreviewApplyCode(value) ||
    isRepairPreviewCode(value) ||
    isRepairApplyCode(value) ||
    isQualityQueryCode(value) ||
    isFileRowQueryCode(value) ||
    isFinalizeBridgeCode(value) ||
    isRecoveryUndoReason(value)
  );
}

function parseJsonRejection(raw: string): {
  reason: BridgeRejectionReason;
  details?: ApplyFailedDetails;
} | null {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(trimmed) as { reason?: unknown; details?: unknown };
    if (typeof parsed.reason !== "string") {
      return null;
    }
    if (!isBridgeRejectionReason(parsed.reason)) {
      return null;
    }
    const details =
      parsed.details && typeof parsed.details === "object" && !Array.isArray(parsed.details)
        ? (parsed.details as ApplyFailedDetails)
        : undefined;
    return { reason: parsed.reason, details };
  } catch {
    return null;
  }
}

/** Map pywebview / mock rejection payloads to BridgeCallError. */
export function toBridgeCallError(err: unknown, method: string): BridgeCallError {
  if (err instanceof BridgeCallError) {
    return err;
  }

  const message = err instanceof Error ? err.message : String(err);
  const json = parseJsonRejection(message);
  if (json) {
    return new BridgeCallError(`Bridge call rejected: ${json.reason}`, {
      code: "rejected",
      method,
      reason: json.reason,
      details: json.details,
      cause: err instanceof Error ? err : undefined,
    });
  }

  if (isBridgeRejectionReason(message)) {
    return new BridgeCallError(`Bridge call rejected: ${message}`, {
      code: "rejected",
      method,
      reason: message,
      cause: err instanceof Error ? err : undefined,
    });
  }

  return new BridgeCallError(`Bridge call failed: ${method}`, {
    code: "rejected",
    method,
    cause: err instanceof Error ? err : undefined,
  });
}
