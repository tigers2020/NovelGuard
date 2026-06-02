import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBridge, useSnapshot } from "../../app/providers/snapshotHooks";
import { formatBytes } from "../../lib/format";
import type { FileRow, FileRowColumnPreset, FileRowDensity } from "../../types/fileRows";
import { StatChip } from "../ui/StatChip";
import { columnsForPreset } from "./shellFileDockColumns";
import {
  clampHeightPx,
  loadShellFileDockState,
  persistShellFileDockState,
  SHELL_FILE_DOCK_DEFAULTS,
} from "./shellFileDockStorage";

const SEARCH_DEBOUNCE_MS = 220;

export function ShellFileDock({ onOpenResolve }: { onOpenResolve: () => void }) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const library = snapshot.library;
  const summary = snapshot.fileListSummary;

  const [expanded, setExpanded] = useState(() => loadShellFileDockState().expanded);
  const [heightPx, setHeightPx] = useState(() => loadShellFileDockState().heightPx);
  const [density, setDensity] = useState<FileRowDensity>(() => loadShellFileDockState().density);
  const [columnPreset, setColumnPreset] = useState<FileRowColumnPreset>(
    () => loadShellFileDockState().columnPreset,
  );
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [rows, setRows] = useState<FileRow[]>([]);
  const [filteredCount, setFilteredCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  const columns = useMemo(() => columnsForPreset(columnPreset), [columnPreset]);
  const rowClass =
    density === "compact" ? "py-1 text-xs" : "py-2 text-sm";

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search]);

  const persist = useCallback(
    (patch: Partial<typeof SHELL_FILE_DOCK_DEFAULTS>) => {
      const next = {
        expanded: patch.expanded ?? expanded,
        heightPx: patch.heightPx ?? heightPx,
        density: patch.density ?? density,
        columnPreset: patch.columnPreset ?? columnPreset,
      };
      persistShellFileDockState(next);
    },
    [columnPreset, density, expanded, heightPx],
  );

  const loadRows = useCallback(async () => {
    if (!expanded) return;
    setLoading(true);
    try {
      setQueryError(null);
      const page = await bridge.queryFileRows({
        search: debouncedSearch || undefined,
        preset: columnPreset,
        cursor: null,
        limit: 100,
      });
      setRows(page.rows);
      setFilteredCount(page.pageInfo.totalFiltered);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Failed to load files");
      setRows([]);
      setFilteredCount(0);
    } finally {
      setLoading(false);
    }
  }, [bridge, columnPreset, debouncedSearch, expanded]);

  useEffect(() => {
    if (!expanded) return;
    const frame = requestAnimationFrame(() => {
      void loadRows();
    });
    return () => cancelAnimationFrame(frame);
  }, [expanded, loadRows, snapshot.work.resolve.libraryRevision]);

  const toggleExpanded = () => {
    const next = !expanded;
    setExpanded(next);
    persist({ expanded: next });
  };

  const totalLabel = library.fileCount.toLocaleString();
  const filteredLabel =
    debouncedSearch && expanded ? filteredCount.toLocaleString() : null;

  return (
    <section
      className={`shrink-0 border-t border-outline bg-surface ${expanded ? "flex min-h-0 flex-col" : ""}`}
      data-testid="shell-file-dock"
      style={expanded ? { height: clampHeightPx(heightPx) } : undefined}
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
        <span className="text-sm text-muted">{totalLabel} files</span>
        {filteredLabel != null && (
          <span className="text-sm text-muted">Showing {filteredLabel}</span>
        )}
        <StatChip label="Dup groups" value={library.duplicateGroups} tone="warn" />
        <StatChip label="Integrity" value={library.integrityIssues} tone="danger" />
        <div className="min-w-0 flex-1 truncate text-xs text-muted">
          {library.folderPath ?? "폴더 미선택"}
        </div>
        <button
          type="button"
          onClick={onOpenResolve}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-background hover:opacity-90"
        >
          검토 · 정리 열기
        </button>
      </header>

      {expanded && (
        <div className="flex min-h-0 flex-1 flex-col border-t border-outline px-4 pb-3">
          <div className="flex flex-wrap items-center gap-2 py-2">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search files..."
              className="min-w-[12rem] flex-1 rounded-md border border-outline bg-surface-elevated px-3 py-1.5 text-sm text-on-surface"
              aria-label="Search files"
            />
            <label className="flex items-center gap-1 text-xs text-muted">
              Preset
              <select
                value={columnPreset}
                onChange={(e) => {
                  const preset = e.target.value as FileRowColumnPreset;
                  setColumnPreset(preset);
                  persist({ columnPreset: preset });
                }}
                className="rounded-md border border-outline bg-surface-elevated px-2 py-1 text-sm"
              >
                <option value="basic">Basic</option>
                <option value="review">Review</option>
              </select>
            </label>
            <button
              type="button"
              className="rounded-md border border-outline px-2 py-1 text-xs"
              onClick={() => {
                const next = density === "comfortable" ? "compact" : "comfortable";
                setDensity(next);
                persist({ density: next });
              }}
            >
              Density: {density === "comfortable" ? "Comfortable" : "Compact"}
            </button>
          </div>

          {library.fileCount === 0 ? (
            <p className="py-4 text-sm text-on-surface-variant">
              스캔된 파일이 없습니다. 작업 탭에서 폴더를 선택하고 스캔하세요.
            </p>
          ) : queryError ? (
            <p className="py-4 text-sm text-error" role="alert">
              {queryError}
            </p>
          ) : (
            <div className="min-h-0 flex-1 overflow-auto rounded-md border border-outline">
              <table className={`w-full min-w-[640px] ${rowClass}`}>
                <thead className="sticky top-0 bg-surface-elevated text-left text-xs text-muted">
                  <tr>
                    {columns.map((col) => (
                      <th key={col.id} className="px-3 font-semibold">
                        {col.header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading && rows.length === 0 ? (
                    <tr>
                      <td colSpan={columns.length} className="px-3 py-4 text-muted">
                        Loading…
                      </td>
                    </tr>
                  ) : rows.length === 0 ? (
                    <tr>
                      <td colSpan={columns.length} className="px-3 py-4 text-muted">
                        No matching files.
                      </td>
                    </tr>
                  ) : (
                    rows.map((row) => (
                      <tr key={row.id} className="border-t border-outline/60 hover:bg-hover">
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
          )}

          <ResizeHandle
            onResize={(delta) => {
              const next = clampHeightPx(heightPx + delta);
              setHeightPx(next);
              persist({ heightPx: next });
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
