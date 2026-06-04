import type { AppSnapshot, WorkMode } from "../types/snapshot";
import type { DuplicateGroupDetail, ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetailResponse, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import type {
  ApplyQualityRepairRequest,
  DiscardQualityRepairPreviewRequest,
  QualityRepairPreviewRequest,
  QualityRepairPreviewResult,
} from "../types/qualityRepair";
import type {
  ApplyResolvedActionsRequest,
  DiscardMovePreviewRequest,
  MovePreviewResult,
} from "../types/movePreview";
import type {
  UpdateReviewDecisionsRequest,
  UpdateReviewDecisionsResult,
} from "../types/reviewDecisions";
import type {
  FinalizeCleanupPreview,
  FinalizeReportDocument,
  FinalizeResult,
  FinalizeSummary,
  RunFinalizeRequest,
} from "../types/finalize";
import type { SelectionScope } from "../types/selection";
import type { AppInfo } from "../types/appInfo";
import type { FileRowsPage, FileRowsQuery } from "../types/fileRows";
import type { LogEntriesPage, LogEntriesQuery, LogsArtifactsResponse } from "../types/logs";
import type { AppSettingKey, AppSettingResponse, AppSettingValue } from "../types/settings";
import type { SnapshotInvalidationEvent } from "../types/snapshotInvalidation";

export interface NovelGuardBridge {
  getAppInfo(): Promise<AppInfo>;
  getSnapshot(): Promise<AppSnapshot>;
  selectFolder(): Promise<void>;
  startScan(options?: Record<string, unknown>): Promise<void>;
  cancelRun(): Promise<void>;
  setWorkMode(mode: WorkMode): Promise<void>;
  queryReviewRows(query: ReviewRowsQuery): Promise<ReviewRowsPage>;
  queryFileRows(query: FileRowsQuery): Promise<FileRowsPage>;
  queryQualityRows(query: QualityRowsQuery): Promise<QualityRowsPage>;
  getDuplicateGroupDetail(groupId: string): Promise<DuplicateGroupDetail>;
  getQualityIssueDetail(issueId: string): Promise<QualityIssueDetailResponse>;
  getQualityRepairPreview(
    request: QualityRepairPreviewRequest,
  ): Promise<QualityRepairPreviewResult>;
  applyQualityRepair(request: ApplyQualityRepairRequest): Promise<void>;
  discardQualityRepairPreview(request: DiscardQualityRepairPreviewRequest): Promise<void>;
  getMovePreview(
    selection: SelectionScope,
    options?: { expectedOperationCount?: number },
  ): Promise<MovePreviewResult>;
  applyResolvedActions(request: ApplyResolvedActionsRequest): Promise<void>;
  discardMovePreview(request: DiscardMovePreviewRequest): Promise<void>;
  updateReviewDecisions(
    request: UpdateReviewDecisionsRequest,
  ): Promise<UpdateReviewDecisionsResult>;
  getAppSetting(key: AppSettingKey): Promise<AppSettingResponse>;
  setAppSetting(key: AppSettingKey, value: AppSettingValue): Promise<AppSettingResponse>;
  queryLogEntries(query: LogEntriesQuery): Promise<LogEntriesPage>;
  getLogsArtifacts(): Promise<LogsArtifactsResponse>;
  getFinalizeSummary(): Promise<FinalizeSummary>;
  previewFinalizeCleanup(): Promise<FinalizeCleanupPreview>;
  runFinalizeVerification(request: RunFinalizeRequest): Promise<FinalizeResult>;
  getFinalizeReport(reportId: string): Promise<FinalizeReportDocument>;
  cancelFinalize(): Promise<void>;
  /** Mock emits events; production bridge may no-op until host push exists. */
  subscribeSnapshotInvalidation(
    listener: (event: SnapshotInvalidationEvent) => void,
  ): () => void;
}
