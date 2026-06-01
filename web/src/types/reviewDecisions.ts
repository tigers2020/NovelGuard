import type { SelectionScope } from "./selection";

export type ReviewDecisionCommand =
  | "approve"
  | "exclude"
  | "setKeeper"
  | "markConflict"
  | "reset";

export interface UpdateReviewDecisionsRequest {
  selection: SelectionScope;
  command: ReviewDecisionCommand;
  keeperFileId?: string;
}

export interface UpdateReviewDecisionsResult {
  updatedCount: number;
  libraryRevision: number;
}
