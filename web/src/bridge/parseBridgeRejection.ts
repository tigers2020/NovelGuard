import type { ApplyFailedDetails, PreviewApplyErrorCode } from "../types/movePreview";
import { BridgeCallError } from "./bridgeErrors";

const PREVIEW_APPLY_CODES: readonly PreviewApplyErrorCode[] = [
  "MISSING_PREVIEW_TOKEN",
  "INVALID_PREVIEW_TOKEN",
  "NO_PENDING_APPLY",
  "STALE_PREVIEW",
  "SELECTION_CHANGED",
  "APPLY_FAILED",
  "LIBRARY_BUSY",
];

function isPreviewApplyCode(value: string): value is PreviewApplyErrorCode {
  return (PREVIEW_APPLY_CODES as readonly string[]).includes(value);
}

function parseJsonRejection(raw: string): { reason: PreviewApplyErrorCode; details?: ApplyFailedDetails } | null {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(trimmed) as { reason?: unknown; details?: unknown };
    if (typeof parsed.reason !== "string" || !isPreviewApplyCode(parsed.reason)) {
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

  if (isPreviewApplyCode(message)) {
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
