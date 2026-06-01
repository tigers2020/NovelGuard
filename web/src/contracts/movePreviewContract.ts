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
  if (p.hasPendingApply !== true) {
    throw new MovePreviewContractError("hasPendingApply must be true on preview");
  }
  if (!Array.isArray(p.rows)) {
    throw new MovePreviewContractError("rows must be an array");
  }
  if (typeof p.summary !== "object" || p.summary === null) {
    throw new MovePreviewContractError("summary must be an object");
  }
}
