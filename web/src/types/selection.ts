import type { ReviewRowsQuery } from "./review";

export type SelectionScope =
  | { type: "explicit_rows"; rowIds: string[] }
  | {
      type: "current_query";
      query: ReviewRowsQuery;
      excludeRowIds: string[];
    };

export class EmptySelectionError extends Error {
  constructor() {
    super("SelectionScope must include at least one row");
    this.name = "EmptySelectionError";
  }
}

export class InvalidSelectionScopeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidSelectionScopeError";
  }
}

export type SelectionScopeResolver = (
  query: ReviewRowsQuery,
  excludeRowIds: string[],
) => number;

/** Validates scope shape and non-empty row coverage when a resolver is provided. */
export function validateSelectionScope(
  selection: SelectionScope,
  resolveCurrentQueryCount?: SelectionScopeResolver,
): void {
  if (selection.type === "explicit_rows") {
    if (selection.rowIds.length === 0) {
      throw new EmptySelectionError();
    }
    return;
  }

  if (selection.type === "current_query") {
    if (!selection.query?.viewMode) {
      throw new InvalidSelectionScopeError("current_query requires a ReviewRowsQuery with viewMode");
    }
    if (!Array.isArray(selection.excludeRowIds)) {
      throw new InvalidSelectionScopeError("excludeRowIds must be an array");
    }
    if (resolveCurrentQueryCount) {
      const count = resolveCurrentQueryCount(selection.query, selection.excludeRowIds);
      if (count === 0) {
        throw new EmptySelectionError();
      }
    }
    return;
  }

  throw new InvalidSelectionScopeError(`Unknown SelectionScope type: ${(selection as { type: string }).type}`);
}
