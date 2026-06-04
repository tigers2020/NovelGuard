import { useMemo } from "react";
import { StatChip } from "../../components/ui/StatChip";
import type {
  FinalizeBlocker,
  FinalizeReportDocument,
  FinalizeResultStatus,
  FinalizeWarning,
} from "../../types/finalize";

const STATUS_LABELS: Record<FinalizeResultStatus, string> = {
  complete: "완료",
  complete_with_warnings: "경고 포함 완료",
  blocked: "차단",
  cancelled: "취소",
  error: "오류",
};

function formatReportTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }
  return new Date(parsed).toLocaleString("ko-KR");
}

function IssueList({
  title,
  items,
  tone,
}: {
  title: string;
  items: FinalizeBlocker[] | FinalizeWarning[];
  tone: "error" | "warning";
}) {
  if (items.length === 0) {
    return null;
  }
  const border = tone === "error" ? "border-error/40" : "border-secondary/40";
  const heading = tone === "error" ? "text-error" : "text-secondary";
  return (
    <section className={`rounded-md border ${border} bg-background px-3 py-3`}>
      <h3 className={`text-sm font-semibold ${heading}`}>{title}</h3>
      <ul className="mt-2 space-y-1 text-sm text-on-surface">
        {items.map((item) => (
          <li key={item.code}>
            {item.message}
            {item.count != null ? ` (${item.count.toLocaleString()}건)` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function FinalizeReportPanel({ report }: { report: FinalizeReportDocument }) {
  const { summary } = report;
  const qualityErrors = summary.quality.encodingIssueCount + summary.quality.integrityIssueCount;

  const statusTone = useMemo(() => {
    switch (report.status) {
      case "complete":
        return "good" as const;
      case "complete_with_warnings":
        return "warn" as const;
      case "blocked":
      case "error":
        return "warn" as const;
      default:
        return undefined;
    }
  }, [report.status]);

  return (
    <section
      className="space-y-4 rounded-md border border-outline bg-surface p-4"
      data-testid="finalize-report-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-on-surface">완료 보고서</h2>
          <p className="mt-1 text-xs text-muted">
            보고서 ID: <span className="font-mono text-on-surface-variant">{report.reportId}</span>
          </p>
          <p className="text-xs text-muted">생성: {formatReportTime(report.createdAt)}</p>
        </div>
        <StatChip label="결과" value={STATUS_LABELS[report.status] ?? report.status} tone={statusTone} />
      </div>

      <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <StatChip label="라이브러리 revision" value={String(report.libraryRevision)} />
        <StatChip label="스캔" value={summary.scanState} />
        <StatChip label="Exact 미해결" value={String(summary.resolve.exactUnresolvedQueueCount)} />
        <StatChip label="품질 이슈" value={String(qualityErrors)} />
      </dl>

      <IssueList title="차단 사유" items={report.blockers} tone="error" />
      <IssueList title="경고" items={report.warnings} tone="warning" />

      <section className="rounded-md border border-outline bg-background px-3 py-3">
        <h3 className="text-sm font-semibold text-on-surface">검토 · 정리</h3>
        <ul className="mt-2 grid gap-1 text-sm text-on-surface sm:grid-cols-2">
          <li>대기열: {summary.resolve.queueCount.toLocaleString()}건</li>
          <li>승인: {summary.resolve.approvedCount.toLocaleString()}건</li>
          <li>충돌: {summary.resolve.conflictCount.toLocaleString()}건</li>
          <li>
            이동 미리보기 대기: {summary.resolve.hasPendingApply ? "예" : "아니오"}
          </li>
        </ul>
      </section>

      <section className="rounded-md border border-outline bg-background px-3 py-3">
        <h3 className="text-sm font-semibold text-on-surface">품질</h3>
        <ul className="mt-2 grid gap-1 text-sm text-on-surface sm:grid-cols-2">
          <li>인코딩: {summary.quality.encodingIssueCount.toLocaleString()}건</li>
          <li>무결성: {summary.quality.integrityIssueCount.toLocaleString()}건</li>
          <li>소용량 이상: {summary.quality.smallFileAnomalyCount.toLocaleString()}건</li>
          <li>
            복구 미리보기 대기: {summary.quality.hasPendingQualityRepair ? "예" : "아니오"}
          </li>
        </ul>
      </section>

      <section className="rounded-md border border-outline bg-background px-3 py-3">
        <h3 className="text-sm font-semibold text-on-surface">적용 이력 (감사 로그 요약)</h3>
        <ul className="mt-2 grid gap-1 text-sm text-on-surface sm:grid-cols-2">
          <li>이동 적용: {report.audit.moveApplyCount.toLocaleString()}회</li>
          <li>복구 적용: {report.audit.repairApplyCount.toLocaleString()}회</li>
          <li>
            마지막 이동:{" "}
            {report.audit.lastMoveApplyAt
              ? formatReportTime(report.audit.lastMoveApplyAt)
              : "—"}
          </li>
          <li>
            마지막 복구:{" "}
            {report.audit.lastRepairApplyAt
              ? formatReportTime(report.audit.lastRepairApplyAt)
              : "—"}
          </li>
        </ul>
      </section>

      <section className="rounded-md border border-outline bg-background px-3 py-3">
        <h3 className="text-sm font-semibold text-on-surface">빈 폴더 정리</h3>
        <p className="mt-1 text-sm text-on-surface">
          미리보기 {report.cleanup.previewedEmptyDirs.length.toLocaleString()}개 · 삭제{" "}
          {report.cleanup.removedEmptyDirs.length.toLocaleString()}개
        </p>
        {report.cleanup.removedEmptyDirs.length > 0 && (
          <ul className="mt-2 max-h-32 list-inside list-disc overflow-y-auto text-xs text-on-surface-variant">
            {report.cleanup.removedEmptyDirs.map((dir) => (
              <li key={dir}>{dir}</li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
