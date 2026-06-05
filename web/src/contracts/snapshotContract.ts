import type { AppSnapshot } from "../types/snapshot";

export const FORBIDDEN_SNAPSHOT_ARRAY_KEYS = [
  "fileList",
  "reviewRows",
  "rows",
  "reviewRowsPage",
  "fileRows",
] as const;

export class SnapshotContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SnapshotContractError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertRequiredFields(snapshot: Record<string, unknown>): void {
  const required = [
    "route",
    "theme",
    "locale",
    "connection",
    "library",
    "pipeline",
    "work",
    "fileListSummary",
  ];
  for (const key of required) {
    if (!(key in snapshot)) {
      throw new SnapshotContractError(`AppSnapshot missing required field: ${key}`);
    }
  }
  if (!isRecord(snapshot.library) || !isRecord(snapshot.pipeline) || !isRecord(snapshot.work)) {
    throw new SnapshotContractError("AppSnapshot nested objects invalid");
  }
  if (!isRecord(snapshot.fileListSummary)) {
    throw new SnapshotContractError("AppSnapshot.fileListSummary must be an object");
  }
  const work = snapshot.work as Record<string, unknown>;
  const resolve = work.resolve;
  if (!isRecord(resolve)) {
    throw new SnapshotContractError("ResolveSnapshot must be an object");
  }
  if (typeof resolve.libraryRevision !== "number") {
    throw new SnapshotContractError("ResolveSnapshot.libraryRevision must be a number");
  }
  for (const key of ["moveReadyCount", "reviewSignalCount"] as const) {
    const value = resolve[key];
    if (typeof value !== "number" || value < 0 || !Number.isInteger(value)) {
      throw new SnapshotContractError(`ResolveSnapshot.${key} must be a non-negative int`);
    }
  }
}

/** Runtime guard: no unbounded row arrays on snapshot payloads. */
export function validateAppSnapshot(snapshot: unknown): asserts snapshot is AppSnapshot {
  if (!isRecord(snapshot)) {
    throw new SnapshotContractError("AppSnapshot must be an object");
  }
  assertRequiredFields(snapshot);

  for (const key of FORBIDDEN_SNAPSHOT_ARRAY_KEYS) {
    if (key in snapshot && Array.isArray(snapshot[key])) {
      throw new SnapshotContractError(`AppSnapshot must not contain array field: ${key}`);
    }
  }
}
