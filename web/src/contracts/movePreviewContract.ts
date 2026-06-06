import type { MovePreviewResult } from "../types/movePreview";

export class MovePreviewContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MovePreviewContractError";
  }
}

export function validateMovePreviewResult(payload: unknown): asserts payload is MovePreviewResult {
  if (typeof payload !== "object" || payload === null) {
    throw new MovePreviewContractError("MovePreviewResult must be an object");
  }
  const p = payload as Record<string, unknown>;
  for (const key of [
    "previewToken",
    "libraryRevision",
    "selectionFingerprint",
    "hasPendingApply",
    "rows",
    "summary",
  ]) {
    if (!(key in p)) {
      throw new MovePreviewContractError(`MovePreviewResult missing ${key}`);
    }
  }
  if (typeof p.previewToken !== "string" || p.previewToken.length === 0) {
    throw new MovePreviewContractError("previewToken invalid");
  }
  if (typeof p.libraryRevision !== "number") {
    throw new MovePreviewContractError("libraryRevision must be a number");
  }
  if (typeof p.selectionFingerprint !== "string" || p.selectionFingerprint.length === 0) {
    throw new MovePreviewContractError("selectionFingerprint invalid");
  }
  const summary = p.summary as Record<string, unknown>;
  const opCount = summary.operationCount;
  if (typeof opCount !== "number") {
    throw new MovePreviewContractError("summary.operationCount must be a number");
  }
  if (Boolean(p.hasPendingApply) !== opCount > 0) {
    throw new MovePreviewContractError("hasPendingApply must match operationCount > 0");
  }
  if (!Array.isArray(p.rows)) {
    throw new MovePreviewContractError("rows must be an array");
  }
  for (const row of p.rows) {
    if (typeof row !== "object" || row === null) {
      throw new MovePreviewContractError("row must be an object");
    }
    const r = row as Record<string, unknown>;
    for (const key of ["id", "action", "name", "sourcePath", "destPath"] as const) {
      if (typeof r[key] !== "string" || r[key].length === 0) {
        throw new MovePreviewContractError(`row missing or empty ${key}`);
      }
    }
  }
  if (typeof p.summary !== "object" || p.summary === null) {
    throw new MovePreviewContractError("summary must be an object");
  }
}
