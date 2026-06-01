import type { AppSnapshot, WorkMode } from "../types/snapshot";
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetail, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewResult,
} from "../types/movePreview";
import type { SelectionScope } from "../types/selection";

export interface NovelGuardBridge {
  getSnapshot(): Promise<AppSnapshot>;
  selectFolder(): Promise<void>;
  startScan(options?: Record<string, unknown>): Promise<void>;
  cancelRun(): Promise<void>;
  setWorkMode(mode: WorkMode): Promise<void>;
  queryReviewRows(query: ReviewRowsQuery): Promise<ReviewRowsPage>;
  queryQualityRows(query: QualityRowsQuery): Promise<QualityRowsPage>;
  getDuplicateGroupDetail(groupId: string): Promise<Record<string, unknown>>;
  getQualityIssueDetail(issueId: string): Promise<QualityIssueDetail>;
  getMovePreview(selection: SelectionScope): Promise<MovePreviewResult>;
  applyResolvedActions(request: ApplyResolvedActionsRequest): Promise<void>;
  discardMovePreview(request: DiscardMovePreviewRequest): Promise<void>;
}
