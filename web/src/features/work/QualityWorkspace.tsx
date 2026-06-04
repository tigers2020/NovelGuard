import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import type {
  QualityIssueDetail,
  QualityIssueType,
  QualityRow,
  QualityRowsPage,
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
import { QualityDetailPanel } from "./quality/QualityDetailPanel";
import { RepairSubflowDialog } from "./RepairSubflowDialog";

const issueTabs: { id: QualityIssueType; label: string }[] = [
  { id: "integrity", label: "무결성" },
  { id: "encoding", label: "인코딩" },
  { id: "small_file", label: "소형 파일" },
];

const emptyTabMessage: Record<QualityIssueType, string> = {
  integrity: "무결성 이슈가 없습니다.",
  encoding: "인코딩 이슈가 없습니다.",
  small_file: "소형 파일 이슈가 없습니다.",
};

export function QualityWorkspace({ onOpenFinalize }: { onOpenFinalize: () => void }) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const snapshot = useSnapshot();
  const quality = snapshot.work.quality;
  const libraryRevision = snapshot.work.resolve.libraryRevision;

  const [issueType, setIssueType] = useState<QualityIssueType>("integrity");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rows, setRows] = useState<QualityRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [tabSummary, setTabSummary] = useState<QualityRowsPage["summary"]>({
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
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);
  const [isWideLayout, setIsWideLayout] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches,
  );

  const detailSeqRef = useRef(0);

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

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const onChange = () => {
      setIsWideLayout(media.matches);
      if (media.matches) {
        setDetailSheetOpen(false);
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    detailSeqRef.current += 1;
    setSelected(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(false);
  }, [issueType]);

  const loadDetail = useCallback(
    async (row: QualityRow | null) => {
      const seq = ++detailSeqRef.current;
      if (!row) {
        if (seq !== detailSeqRef.current) return;
        setDetail(null);
        setDetailError(null);
        setDetailLoading(false);
        return;
      }
      setDetailLoading(true);
      setDetailError(null);
      try {
        const payload = await bridge.getQualityIssueDetail(row.id);
        if (seq !== detailSeqRef.current) return;
        if (payload.status === "not_found") {
          setDetail(null);
          setDetailError("이슈를 찾을 수 없습니다.");
          return;
        }
        setDetail(payload.detail);
      } catch (err) {
        if (seq !== detailSeqRef.current) return;
        setDetail(null);
        setDetailError(err instanceof Error ? err.message : "Failed to load detail");
      } finally {
        if (seq === detailSeqRef.current) {
          setDetailLoading(false);
        }
      }
    },
    [bridge],
  );

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean, preserveRowId?: string | null) => {
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
        setFilteredCount(page.pageInfo.totalFiltered);
        setTabSummary(page.summary);
        setNextCursor(page.pageInfo.nextCursor);
        setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
        if (!append) {
          const next =
            preserveRowId != null
              ? (page.rows.find((r) => r.id === preserveRowId) ?? page.rows[0] ?? null)
              : (page.rows[0] ?? null);
          setSelected(next);
          void loadDetail(next);
        }
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load quality rows");
        if (!append) {
          setRows([]);
          setNextCursor(null);
          setFilteredCount(0);
          setTabSummary({ issueCount: 0, warningCount: 0, errorCount: 0 });
          setSelected(null);
          setDetail(null);
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
    void loadPage(null, false, selected?.id ?? null);
  }, [libraryRevision, loadPage, selected?.id]);

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
    if (!isWideLayout) {
      setDetailSheetOpen(true);
    }
    void loadDetail(row);
  };

  const handleDetailRetry = () => {
    if (selected) void loadDetail(selected);
  };

  const handleRepairSuccess = async () => {
    await refreshSnapshot();
    const preserveId = selected?.id ?? null;
    await loadPage(null, false, preserveId);
  };

  const activeTabLabel = issueTabs.find((t) => t.id === issueType)?.label ?? issueType;
  const showEmptyTab = !loading && !queryError && rows.length === 0;

  const detailPanel = (
    <QualityDetailPanel
      selectedRow={selected}
      detail={detail}
      loading={detailLoading}
      error={detailError}
      stale={detailStale}
      onRetry={handleDetailRetry}
      onOpenRepair={() => setRepairOpen(true)}
      onClose={!isWideLayout ? () => setDetailSheetOpen(false) : undefined}
    />
  );

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background"
      data-testid="quality-workspace"
    >
      <section className="shrink-0 border-b border-outline bg-surface p-5">
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
              data-testid={`quality-tab-${tab.id}`}
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
        {loading && !queryError && (
          <p className="mt-2 text-xs text-muted" data-testid="quality-grid-loading">
            {activeTabLabel} 탭 불러오는 중…
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
        {!loading && !queryError && filteredCount > 0 && (
          <p className="mt-2 text-xs text-on-surface-variant" data-testid="quality-tab-summary">
            {activeTabLabel}: {filteredCount.toLocaleString()}건 (경고{" "}
            {tabSummary.warningCount.toLocaleString()} · 오류{" "}
            {tabSummary.errorCount.toLocaleString()})
          </p>
        )}
      </section>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {!isWideLayout && selected && (
            <div className="flex shrink-0 items-center justify-between gap-2 border-b border-outline bg-surface px-3 py-2">
              <p className="truncate text-xs text-on-surface-variant">
                선택: <span className="font-semibold text-on-surface">{selected.name}</span>
              </p>
              <button
                type="button"
                data-testid="quality-detail-sheet-open"
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-background"
                onClick={() => setDetailSheetOpen(true)}
              >
                상세 보기
              </button>
            </div>
          )}

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-5 pt-4">
            {showEmptyTab && (
              <p
                className="mb-3 rounded-md border border-outline bg-surface p-4 text-sm text-on-surface-variant"
                data-testid="quality-tab-empty"
                role="status"
              >
                {emptyTabMessage[issueType]}
              </p>
            )}
            <VirtualizedQualityGrid
              rows={rows}
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
              filteredCount={filteredCount}
              tabSummary={tabSummary}
            />
          </div>
        </div>

        {isWideLayout && (
          <QualityDetailPanel
            className="w-[min(360px,36%)] shrink-0 border-l border-outline"
            selectedRow={selected}
            detail={detail}
            loading={detailLoading}
            error={detailError}
            stale={detailStale}
            onRetry={handleDetailRetry}
            onOpenRepair={() => setRepairOpen(true)}
          />
        )}
      </div>

      {!isWideLayout && detailSheetOpen && (
        <div
          className="fixed inset-0 z-40 flex flex-col bg-background/95 backdrop-blur-sm"
          data-testid="quality-detail-sheet"
          role="dialog"
          aria-modal="true"
        >
          {detailPanel}
        </div>
      )}

      <RepairSubflowDialog
        open={repairOpen}
        issueId={selected?.id ?? null}
        snapshotLibraryRevision={libraryRevision}
        onClose={() => setRepairOpen(false)}
        onSuccess={() => void handleRepairSuccess()}
        onOpenFinalize={onOpenFinalize}
      />
    </main>
  );
}
