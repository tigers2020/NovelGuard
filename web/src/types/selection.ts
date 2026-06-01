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
