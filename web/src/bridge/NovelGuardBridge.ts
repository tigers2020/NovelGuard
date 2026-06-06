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
import type { AutoSelectKeepersSummary } from "../types/autoSelectSummary";
import type { ResolveAutoApproveSummary } from "../types/resolveAutoApproveSummary";
import type {
  UpdateReviewDecisionsRequest,
  UpdateReviewDecisionsResult,
} from "../types/reviewDecisions";
import type {
  FinalizeCleanupPreview,
  FinalizeReportDocument,
  FinalizeSummary,
  RunFinalizeRequest,
} from "../types/finalize";
import type { FinalizeJobSnapshot } from "../types/finalizeJob";
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
  getMovePreview(selection: SelectionScope): Promise<MovePreviewResult>;
  applyResolvedActions(request: ApplyResolvedActionsRequest): Promise<void>;
  discardMovePreview(request: DiscardMovePreviewRequest): Promise<void>;
  updateReviewDecisions(
    request: UpdateReviewDecisionsRequest,
  ): Promise<UpdateReviewDecisionsResult>;
  summarizeAutoSelectKeepers(query: ReviewRowsQuery): Promise<AutoSelectKeepersSummary>;
  summarizeResolveAutoApprove(query: ReviewRowsQuery): Promise<ResolveAutoApproveSummary>;
  startResolveAutoApproveJob(query: ReviewRowsQuery): Promise<{ accepted: true }>;
  cancelResolveAutoApproveJob(): Promise<void>;
  getAppSetting(key: AppSettingKey): Promise<AppSettingResponse>;
  setAppSetting(key: AppSettingKey, value: AppSettingValue): Promise<AppSettingResponse>;
  queryLogEntries(query: LogEntriesQuery): Promise<LogEntriesPage>;
  getLogsArtifacts(): Promise<LogsArtifactsResponse>;
  getFinalizeSummary(): Promise<FinalizeSummary>;
  previewFinalizeCleanup(): Promise<FinalizeCleanupPreview>;
  startFinalizeJob(request: RunFinalizeRequest): Promise<FinalizeJobSnapshot>;
  getFinalizeJob(): Promise<FinalizeJobSnapshot>;
  getFinalizeReport(reportId: string): Promise<FinalizeReportDocument>;
  cancelFinalize(): Promise<void>;
  /** Mock emits events; production bridge may no-op until host push exists. */
  subscribeSnapshotInvalidation(
    listener: (event: SnapshotInvalidationEvent) => void,
  ): () => void;
}
