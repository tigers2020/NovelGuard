import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { useBridge, useSnapshot } from "../../app/providers/snapshotHooks";
import type {
  QualityIssueDetail,
  QualityIssueType,
  QualityRow,
} from "../../types/quality";
import { ColumnChooser } from "../../components/grid/ColumnChooser";
import { StatChip } from "../../components/ui/StatChip";
import {
  OPTIONAL_QUALITY_COLUMN_KEYS,
  QUALITY_GRID_SIZING_KEY,
} from "./quality/qualityGridColumns";
import {
  loadQualityColumnSizing,
  loadQualityColumnVisibility,
  saveQualityColumnVisibility,
} from "./quality/qualityGridPersistence";
import { VirtualizedQualityGrid } from "./quality/VirtualizedQualityGrid";
import { RepairSubflowDialog } from "./RepairSubflowDialog";

const issueTabs: { id: QualityIssueType; label: string }[] = [
  { id: "integrity", label: "무결성" },
  { id: "encoding", label: "인코딩" },
  { id: "small_file", label: "소형 파일" },
];

export function QualityWorkspace({ onOpenFinalize }: { onOpenFinalize: () => void }) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const quality = snapshot.work.quality;
  const libraryRevision = snapshot.work.resolve.libraryRevision;

  const [issueType, setIssueType] = useState<QualityIssueType>("integrity");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rows, setRows] = useState<QualityRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [tabSummary, setTabSummary] = useState({
    issueCount: 0,
    warningCount: 0,
    errorCount: 0,
  });
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [columnVisibility, setColumnVisibility] = useState(loadQualityColumnVisibility);
  const [columnSizing, setColumnSizing] = useState(loadQualityColumnSizing);
  const [selected, setSelected] = useState<QualityRow | null>(null);
  const [detail, setDetail] = useState<QualityIssueDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [repairOpen, setRepairOpen] = useState(false);

  const detailStale = useMemo(
    () => detail !== null && detail.libraryRevision !== libraryRevision,
    [detail, libraryRevision],
  );

  const currentSort = useMemo(() => {
    const primary = sorting[0];
    if (!primary) return undefined;
    return {
      field: primary.id,
      direction: primary.desc ? ("desc" as const) : ("asc" as const),
    };
  }, [sorting]);

  const loadDetail = useCallback(
    (row: QualityRow | null) => {
      if (!row) {
        setDetail(null);
        setDetailError(null);
        return;
      }
      setDetailLoading(true);
      void bridge
        .getQualityIssueDetail(row.id)
        .then((payload) => {
          if (payload.status === "not_found") {
            setDetail(null);
            setDetailError("이슈를 찾을 수 없습니다.");
            return;
          }
          setDetail(payload.detail);
          setDetailError(null);
        })
        .catch((err) => {
          setDetail(null);
          setDetailError(err instanceof Error ? err.message : "Failed to load detail");
        })
        .finally(() => setDetailLoading(false));
    },
    [bridge],
  );

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      try {
        setQueryError(null);
        const page = await bridge.queryQualityRows({
          issueType,
          cursor,
          limit: 100,
          sort: currentSort,
        });
        setNextCursor(page.pageInfo.nextCursor);
        if (!append) {
          setFilteredCount(page.pageInfo.totalFiltered);
          setTabSummary(page.summary);
        }
        setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
        if (!append) {
          const first = page.rows[0] ?? null;
          setSelected(first);
          loadDetail(first);
        }
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load quality rows");
        if (!append) {
          setRows([]);
          setNextCursor(null);
          setFilteredCount(0);
          setTabSummary({ issueCount: 0, warningCount: 0, errorCount: 0 });
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [bridge, issueType, currentSort, loadDetail],
  );

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadPage(null, false);
    });
    return () => cancelAnimationFrame(frame);
  }, [loadPage]);

  const seenRevisionRef = useRef<number | null>(null);
  useEffect(() => {
    if (seenRevisionRef.current === null) {
      seenRevisionRef.current = libraryRevision;
      return;
    }
    if (seenRevisionRef.current === libraryRevision) return;
    seenRevisionRef.current = libraryRevision;
    void loadPage(null, false);
  }, [libraryRevision, loadPage]);

  const loadingMoreRef = useRef(false);
  const handleNearEnd = () => {
    if (!nextCursor || loadingMore || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    void loadPage(nextCursor, true).finally(() => {
      loadingMoreRef.current = false;
    });
  };

  const handleSelect = (row: QualityRow) => {
    setSelected(row);
    loadDetail(row);
  };

  const handleDetailRetry = () => {
    if (selected) loadDetail(selected);
  };

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background p-5"
      data-testid="quality-workspace"
    >
      <section className="shrink-0 rounded-md border border-outline bg-surface p-5">
        <h1 className="text-xl font-bold text-on-surface">품질 · 무결성</h1>
        <p className="mt-1 text-sm text-on-surface-variant">품질 이슈 검토 · UTF-8 복구 (단건)</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <StatChip label="Integrity" value={quality.integrityIssueCount} tone="danger" />
          <StatChip label="Encoding" value={quality.encodingIssueCount} tone="warn" />
          <StatChip label="Small files" value={quality.smallFileAnomalyCount} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {issueTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setIssueType(tab.id)}
              className={`rounded-md px-3 py-2 text-sm font-semibold ${
                issueType === tab.id
                  ? "bg-primary text-background"
                  : "border border-outline text-on-surface-variant hover:bg-hover"
              }`}
            >
              {tab.label}
            </button>
          ))}
          <ColumnChooser
            testId="quality-column-chooser"
            visibility={columnVisibility}
            optionalKeys={OPTIONAL_QUALITY_COLUMN_KEYS}
            onChange={(key, visible) => {
              setColumnVisibility((prev) => {
                const next = { ...prev, [key]: visible };
                saveQualityColumnVisibility(next);
                return next;
              });
            }}
          />
          <button
            type="button"
            data-testid="quality-open-finalize"
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface-variant hover:bg-hover"
            onClick={onOpenFinalize}
          >
            최종 검증
          </button>
        </div>
        <p className="mt-2 text-xs text-muted" data-testid="quality-tab-summary">
          필터 {filteredCount.toLocaleString()}건 · 이슈 {tabSummary.issueCount} · 경고{" "}
          {tabSummary.warningCount} · 오류 {tabSummary.errorCount}
        </p>
        {loading && !queryError && (
          <p className="mt-2 text-xs text-muted" data-testid="quality-grid-loading">
            Loading rows…
          </p>
        )}
        {queryError && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-sm text-error" data-testid="quality-query-error">
              {queryError}
            </p>
            <button
              type="button"
              data-testid="quality-query-retry"
              className="rounded-md border border-outline px-3 py-1 text-sm font-semibold text-on-surface hover:bg-hover"
              onClick={() => void loadPage(null, false)}
            >
              Retry
            </button>
          </div>
        )}
      </section>

      <div className="mt-4 grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_280px]">
        <VirtualizedQualityGrid
          rows={rows}
          filteredCount={filteredCount}
          selectedRowId={selected?.id ?? null}
          onSelectRow={handleSelect}
          onNearEnd={handleNearEnd}
          loadingMore={loadingMore}
          sorting={sorting}
          onSortingChange={setSorting}
          userColumnVisibility={columnVisibility}
          columnSizing={columnSizing}
          onColumnSizingChange={(next) => {
            setColumnSizing(next);
            localStorage.setItem(QUALITY_GRID_SIZING_KEY, JSON.stringify(next));
          }}
        />
        <aside className="overflow-y-auto rounded-md border border-outline bg-surface p-4 text-sm">
          <p className="font-semibold text-on-surface">Issue detail</p>
          {detailLoading && <p className="mt-2 text-muted">불러오는 중…</p>}
          {detailError && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-error" data-testid="quality-detail-error">
                {detailError}
              </p>
              <button
                type="button"
                data-testid="quality-detail-retry"
                className="rounded-md border border-outline px-2 py-1 text-xs font-semibold hover:bg-hover"
                onClick={handleDetailRetry}
              >
                Retry
              </button>
            </div>
          )}
          {detailStale && (
            <p
              className="mt-2 rounded-md border border-outline bg-surface-elevated p-2 text-warning"
              data-testid="quality-detail-stale"
              role="status"
            >
              라이브러리가 변경되었습니다. 목록을 새로고침하거나 행을 다시 선택하세요.
            </p>
          )}
          {detail && !detailError ? (
            <dl className={`mt-3 space-y-2 ${detailStale ? "opacity-60" : ""}`}>
              <div>
                <dt className="text-muted">Name</dt>
                <dd>{detail.name}</dd>
              </div>
              <div>
                <dt className="text-muted">Path</dt>
                <dd className="break-all">{detail.path}</dd>
              </div>
              <div>
                <dt className="text-muted">Encoding</dt>
                <dd>{detail.encoding}</dd>
              </div>
              <div>
                <dt className="text-muted">Severity</dt>
                <dd>{detail.severity}</dd>
              </div>
              <div>
                <dt className="text-muted">Evidence</dt>
                <dd>
                  {detail.evidence.kind}: {detail.evidence.message}
                </dd>
              </div>
              <div>
                <dt className="text-muted">File size</dt>
                <dd>{detail.file.sizeBytes} bytes</dd>
              </div>
              <div>
                <dt className="text-muted">Repair</dt>
                <dd>{detail.repairEligibility.label}</dd>
              </div>
              {detail.repairEligibility.eligible && !detailStale && (
                <button
                  type="button"
                  data-testid="quality-repair-open"
                  className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:bg-primary/90"
                  onClick={() => setRepairOpen(true)}
                >
                  복구 미리보기
                </button>
              )}
              {import.meta.env.DEV && (
                <div>
                  <dt className="text-muted">Raw (dev)</dt>
                  <dd>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-background p-2 text-xs">
                      {JSON.stringify(detail, null, 2)}
                    </pre>
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            !detailLoading &&
            !detailError && <p className="mt-2 text-muted">행을 선택하세요.</p>
          )}
        </aside>
      </div>
      <RepairSubflowDialog
        open={repairOpen}
        issueId={selected?.id ?? null}
        snapshotLibraryRevision={libraryRevision}
        onClose={() => setRepairOpen(false)}
        onSuccess={() => {
          void loadPage(null, false);
          if (selected) {
            loadDetail(selected);
          }
        }}
        onOpenFinalize={onOpenFinalize}
      />
    </main>
  );
}
