import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { withDegradedBridgeRetry } from "../../features/shared/useDegradedBridgeQuery";
import { formatBytes } from "../../lib/format";
import type {
  FileRow,
  FileRowColumnPreset,
  FileRowDensity,
  FileRowsQuery,
  FileRowSortDirection,
  FileRowSortField,
} from "../../types/fileRows";
import { StatChip } from "../ui/StatChip";
import { columnsForPreset } from "./shellFileDockColumns";
import {
  clampHeightPx,
  loadShellFileDockLayout,
  persistFileDockExpandedForMode,
  persistShellFileDockLayout,
} from "./shellFileDockStorage";
import { deriveShellFileDockState } from "./shellFileDockState";
import { shouldClearRowsOnFetchFailure } from "./shellFileDockQueryPolicy";

const SEARCH_DEBOUNCE_MS = 220;
const PAGE_LIMIT = 100;

type SortState = {
  field: FileRowSortField;
  direction: FileRowSortDirection;
};

const DEFAULT_SORT: SortState = { field: "path", direction: "asc" };

export function ShellFileDock({
  expanded,
  onExpandedChange,
  preferFlexHeight = false,
}: {
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  /** When true (Scan primary), expanded dock fills remaining main column height. */
  preferFlexHeight?: boolean;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const snapshot = useSnapshot();
  const library = snapshot.library;
  const activeMode = snapshot.work.activeMode;
  const pipeline = snapshot.pipeline;
  const summary = snapshot.fileListSummary;
  const libraryRevision = snapshot.work.resolve.libraryRevision;
  const [heightPx, setHeightPx] = useState(() => loadShellFileDockLayout().heightPx);
  const [density, setDensity] = useState<FileRowDensity>(() => loadShellFileDockLayout().density);
  const [columnPreset, setColumnPreset] = useState<FileRowColumnPreset>(
    () => loadShellFileDockLayout().columnPreset,
  );
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [rows, setRows] = useState<FileRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [isSelectingFolder, setIsSelectingFolder] = useState(false);

  const pipelineBusy = Boolean(pipeline.background?.active);
  const deepAnalysisRunning = snapshot.work.scan.deepAnalysisStatus === "running";
  const isExpectedSlow = pipelineBusy || deepAnalysisRunning;
  const showDegradedBanner = degraded || isExpectedSlow;

  const columns = useMemo(() => columnsForPreset(columnPreset), [columnPreset]);
  const rowClass =
    density === "compact" ? "py-1 text-xs" : "py-2 text-sm";

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search]);

  const persistLayout = useCallback(
    (patch: Partial<{ heightPx: number; density: FileRowDensity; columnPreset: FileRowColumnPreset }>) => {
      persistShellFileDockLayout({
        heightPx: patch.heightPx ?? heightPx,
        density: patch.density ?? density,
        columnPreset: patch.columnPreset ?? columnPreset,
      });
    },
    [columnPreset, density, heightPx],
  );

  const buildQuery = useCallback(
    (cursor: string | null): FileRowsQuery => ({
      search: debouncedSearch || undefined,
      preset: columnPreset,
      cursor,
      limit: PAGE_LIMIT,
      sort,
    }),
    [columnPreset, debouncedSearch, sort],
  );

  const fetchPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (!expanded) return;
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      try {
        setQueryError(null);
        const result = await withDegradedBridgeRetry(() => bridge.queryFileRows(buildQuery(cursor)));
        if (result.ok) {
          const page = result.value;
          setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
          setFilteredCount(page.pageInfo.totalFiltered);
          setNextCursor(page.pageInfo.nextCursor);
          setHasMore(page.pageInfo.hasMore);
          setDegraded(false);
          return;
        }
        if (result.timedOut) {
          setDegraded(true);
          setQueryError(null);
          return;
        }
        throw result.error;
      } catch (err) {
        const message =
          err instanceof BridgeCallError && err.reason
            ? err.reason
            : err instanceof Error
              ? err.message
              : "Failed to load files";
        setQueryError(message);
        if (shouldClearRowsOnFetchFailure(false, append)) {
          setRows([]);
          setFilteredCount(0);
          setNextCursor(null);
          setHasMore(false);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [bridge, buildQuery, expanded],
  );

  const handleSelectFolder = async () => {
    setIsSelectingFolder(true);
    try {
      await bridge.selectFolder();
      await refreshSnapshot();
    } finally {
      setIsSelectingFolder(false);
    }
  };

  useEffect(() => {
    if (!expanded) return;
    const frame = requestAnimationFrame(() => {
      void fetchPage(null, false);
    });
    return () => cancelAnimationFrame(frame);
  }, [expanded, fetchPage, libraryRevision]);

  const dockState = deriveShellFileDockState({ fileCount: library.fileCount, expanded });

  const toggleExpanded = () => {
    const next = !expanded;
    onExpandedChange(next);
    persistFileDockExpandedForMode(activeMode, next);
  };

  const handleSortHeader = (field: FileRowSortField) => {
    setSort((prev) =>
      prev.field === field
        ? { field, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { field, direction: "asc" },
    );
  };

  const sortIndicator = (field: FileRowSortField) => {
    if (sort.field !== field) return "";
    return sort.direction === "asc" ? " ▲" : " ▼";
  };

  const totalLabel = library.fileCount.toLocaleString();
  const filteredLabel =
    debouncedSearch && expanded ? filteredCount.toLocaleString() : null;

  const useFlexHeight = expanded && preferFlexHeight;

  return (
    <section
      className={`border-t border-outline bg-surface ${
        expanded ? `flex min-h-0 flex-col ${useFlexHeight ? "min-h-0 flex-1" : "shrink-0"}` : "shrink-0"
      }`}
      data-testid="shell-file-dock"
      data-state={dockState}
      style={expanded && !useFlexHeight ? { height: clampHeightPx(heightPx) } : undefined}
    >
      <header className="flex flex-wrap items-center gap-2 px-4 py-2">
        <button
          type="button"
          className="rounded-md px-2 py-1 text-sm font-semibold text-on-surface hover:bg-hover"
          aria-expanded={expanded}
          onClick={toggleExpanded}
        >
          {expanded ? "▾" : "▸"} 파일 목록
        </button>
        <span className="text-sm text-muted">{totalLabel}개 파일</span>
        {filteredLabel != null && (
          <span className="text-sm text-muted">표시 {filteredLabel}개</span>
        )}
        <StatChip label="중복 그룹" value={library.duplicateGroups} tone="warn" />
        <StatChip label="무결성" value={library.integrityIssues} tone="danger" />
        <div className="min-w-0 flex-1 truncate text-xs text-muted">
          {library.folderPath ?? "폴더 미선택"}
        </div>
        {preferFlexHeight && (
          <button
            type="button"
            data-testid="shell-file-dock-select-folder"
            disabled={isSelectingFolder || pipeline.phase === "probe" || pipeline.phase === "persist"}
            onClick={() => void handleSelectFolder()}
            className="shrink-0 rounded-md border border-outline px-3 py-1.5 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSelectingFolder ? "선택 중…" : "폴더 선택"}
          </button>
        )}
      </header>

      {expanded && (
        <div className="flex min-h-0 flex-1 flex-col border-t border-outline px-4 pb-3">
          <div className="flex flex-wrap items-center gap-2 py-2">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="파일 검색…"
              className="min-w-[12rem] flex-1 rounded-md border border-outline bg-surface-elevated px-3 py-1.5 text-sm text-on-surface"
              aria-label="파일 검색"
              data-testid="shell-file-dock-search"
            />
            <label className="flex items-center gap-1 text-xs text-muted">
              프리셋
              <select
                value={columnPreset}
                onChange={(e) => {
                  const preset = e.target.value as FileRowColumnPreset;
                  setColumnPreset(preset);
                  persistLayout({ columnPreset: preset });
                }}
                className="rounded-md border border-outline bg-surface-elevated px-2 py-1 text-sm"
              >
                <option value="basic">기본</option>
                <option value="review">검토</option>
                <option value="technical">기술</option>
              </select>
            </label>
            <button
              type="button"
              className="rounded-md border border-outline px-2 py-1 text-xs"
              onClick={() => {
                const next = density === "comfortable" ? "compact" : "comfortable";
                setDensity(next);
                persistLayout({ density: next });
              }}
            >
              밀도: {density === "comfortable" ? "보통" : "촘촘"}
            </button>
          </div>

          {showDegradedBanner && library.fileCount > 0 && (
            <p className="py-2 text-sm text-amber-600" data-testid="shell-file-dock-degraded">
              백그라운드 분석 중 — 목록 일부만 표시됨
              <span className="block text-xs text-muted-foreground">
                계속 불러오는 중입니다. 이미 불러온 항목은 유지됩니다.
              </span>
            </p>
          )}

          {library.fileCount === 0 ? (
            <div className="py-4 text-sm text-on-surface-variant">
              <p>스캔된 파일이 없습니다. 위 스캔 탭에서 폴더를 선택하고 스캔하세요.</p>
            </div>
          ) : queryError ? (
            <div className="flex flex-col gap-2 py-4" role="alert">
              <p className="text-sm text-error" data-testid="shell-file-dock-query-error">
                {queryError}
              </p>
              <button
                type="button"
                data-testid="shell-file-dock-query-retry"
                className="self-start rounded-md border border-outline px-3 py-1.5 text-sm font-semibold hover:bg-hover"
                onClick={() => void fetchPage(null, false)}
              >
                다시 불러오기
              </button>
            </div>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col gap-2">
              <div className="min-h-0 flex-1 overflow-auto rounded-md border border-outline">
                <table className={`w-full min-w-[640px] ${rowClass}`} data-testid="shell-file-dock-table">
                  <thead className="sticky top-0 bg-surface-elevated text-left text-xs text-muted">
                    <tr>
                      {columns.map((col) =>
                        col.sortField ? (
                          <th key={col.id} className="px-3 font-semibold">
                            <button
                              type="button"
                              className="text-left hover:text-on-surface"
                              data-testid={`shell-file-dock-sort-${col.id}`}
                              onClick={() => handleSortHeader(col.sortField!)}
                            >
                              {col.header}
                              {sortIndicator(col.sortField)}
                            </button>
                          </th>
                        ) : (
                          <th key={col.id} className="px-3 font-semibold">
                            {col.header}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {loading && rows.length === 0 ? (
                      <tr>
                        <td colSpan={columns.length} className="px-3 py-4 text-muted">
                          불러오는 중…
                        </td>
                      </tr>
                    ) : rows.length === 0 ? (
                      <tr>
                        <td colSpan={columns.length} className="px-3 py-4 text-muted">
                          일치하는 파일이 없습니다.
                        </td>
                      </tr>
                    ) : (
                      rows.map((row) => (
                        <tr
                          key={row.id}
                          className="border-t border-outline/60 hover:bg-hover"
                          data-testid={`shell-file-dock-row-${row.id}`}
                        >
                          {columns.map((col) => (
                            <td key={col.id} className="max-w-xs truncate px-3">
                              {col.cell(row)}
                            </td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {hasMore && (
                <button
                  type="button"
                  data-testid="shell-file-dock-load-more"
                  className="self-center rounded-md border border-outline px-4 py-1.5 text-sm hover:bg-hover"
                  disabled={loadingMore}
                  onClick={() => void fetchPage(nextCursor, true)}
                >
                  {loadingMore ? "불러오는 중…" : "더 보기"}
                </button>
              )}
            </div>
          )}

          <ResizeHandle
            onResize={(delta) => {
              const next = clampHeightPx(heightPx + delta);
              setHeightPx(next);
              persistLayout({ heightPx: next });
            }}
          />
        </div>
      )}

      {!expanded && library.fileCount > 0 && (
        <p className="sr-only">
          Total size {formatBytes(library.totalBytes)}; issues {summary.issueCount}
        </p>
      )}
    </section>
  );
}

function ResizeHandle({ onResize }: { onResize: (deltaY: number) => void }) {
  const dragging = useRef(false);
  const lastY = useRef(0);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = lastY.current - e.clientY;
      lastY.current = e.clientY;
      if (delta !== 0) onResize(delta);
    };
    const onUp = () => {
      dragging.current = false;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [onResize]);

  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className="mt-2 h-1 cursor-row-resize rounded bg-outline/80"
      onMouseDown={(e) => {
        dragging.current = true;
        lastY.current = e.clientY;
      }}
    />
  );
}
