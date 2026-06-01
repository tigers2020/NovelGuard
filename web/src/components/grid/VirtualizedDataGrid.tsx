import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type OnChangeFn,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { buildColumnGridTemplate, getColumnWidthPx } from "./gridColumnWidths";
import "./gridColumnMeta";

export type VirtualizedDataGridProps<T> = {
  data: T[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<T, any>[];
  getRowId: (row: T) => string;
  selectedRowId?: string | null;
  onSelectRow?: (row: T) => void;
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  columnVisibility?: VisibilityState;
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>;
  /** Viewport-based column visibility (e.g. responsive hide). */
  mergeColumnVisibility?: (containerWidth: number) => VisibilityState;
  columnSizing?: Record<string, number>;
  onColumnSizingChange?: (next: Record<string, number>) => void;
  enableColumnResize?: boolean;
  estimateRowHeight?: number;
  overscan?: number;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  footer?: ReactNode;
  testId?: string;
  headerTestIdPrefix?: string;
};

export function VirtualizedDataGrid<T>({
  data,
  columns,
  getRowId,
  selectedRowId,
  onSelectRow,
  sorting = [],
  onSortingChange,
  columnVisibility,
  onColumnVisibilityChange,
  mergeColumnVisibility,
  columnSizing = {},
  onColumnSizingChange,
  enableColumnResize = false,
  estimateRowHeight = 48,
  overscan = 8,
  onNearEnd,
  footer,
  testId,
  headerTestIdPrefix = "grid-header",
}: VirtualizedDataGridProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useLayoutEffect(() => {
    const el = parentRef.current;
    if (el) setContainerWidth(el.clientWidth);
  }, []);

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setContainerWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const effectiveVisibility = useMemo(() => {
    if (mergeColumnVisibility) return mergeColumnVisibility(containerWidth);
    return columnVisibility;
  }, [columnVisibility, containerWidth, mergeColumnVisibility]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility },
    onSortingChange,
    onColumnVisibilityChange,
    manualSorting: true,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => getRowId(row),
  });

  const { rows } = table.getRowModel();
  const visibleColumns = table
    .getAllLeafColumns()
    .filter((col) => effectiveVisibility?.[col.id] === true);

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateRowHeight,
    overscan,
  });

  const handleScroll = () => {
    const el = parentRef.current;
    if (!el || !onNearEnd) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 120) {
      onNearEnd();
    }
  };

  const gridTemplate = buildColumnGridTemplate(visibleColumns, columnSizing);

  const startColumnResize = useCallback(
    (columnId: string, startX: number) => {
      if (!onColumnSizingChange) return;
      const column = visibleColumns.find((c) => c.id === columnId);
      if (!column) return;

      const startWidth = getColumnWidthPx(column, columnSizing);
      const minPx = column.columnDef.meta?.minWidthPx ?? 48;

      const onMove = (ev: MouseEvent) => {
        const next = Math.max(minPx, startWidth + (ev.clientX - startX));
        onColumnSizingChange({ ...columnSizing, [columnId]: next });
      };
      const onUp = () => {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [columnSizing, onColumnSizingChange, visibleColumns],
  );

  const isColumnResizable = (columnId: string) => {
    if (!enableColumnResize || !onColumnSizingChange) return false;
    const column = visibleColumns.find((c) => c.id === columnId);
    if (!column) return false;
    const meta = column.columnDef.meta;
    return meta?.resizable !== false;
  };

  return (
    <section
      data-testid={testId}
      className="flex h-full max-h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden border-r border-outline bg-background"
    >
      <div
        ref={parentRef}
        data-testid="grid-scroll-body"
        className="min-h-0 flex-1 overflow-auto"
        onScroll={handleScroll}
      >
        <div className="min-w-max">
          <div
            className="sticky top-0 z-10 grid border-b border-outline bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
            style={{ gridTemplateColumns: gridTemplate }}
          >
            {table.getHeaderGroups().map((hg) =>
              hg.headers
                .filter((header) => effectiveVisibility?.[header.column.id] === true)
                .map((header) => {
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();
                const resizable = isColumnResizable(header.column.id);
                return (
                  <div key={header.id} className="relative flex min-w-0 items-stretch">
                    <button
                      type="button"
                      data-testid={`${headerTestIdPrefix}-${header.column.id}`}
                      disabled={!canSort}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                      className={`min-w-0 flex-1 truncate pr-2 text-left ${canSort ? "cursor-pointer hover:text-on-surface" : "cursor-default"}`}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : null}
                    </button>
                    {resizable ? (
                      <div
                        role="separator"
                        aria-orientation="vertical"
                        aria-label={`Resize ${header.column.id} column`}
                        data-testid={`grid-resize-handle-${header.column.id}`}
                        className="absolute top-0 right-0 z-20 h-full w-2 shrink-0 cursor-col-resize touch-none select-none bg-outline/30 hover:bg-primary/50"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          startColumnResize(header.column.id, e.clientX);
                        }}
                      />
                    ) : null}
                  </div>
                );
              }),
            )}
          </div>
          <div
            className="pointer-events-none relative w-full"
            style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const row = rows[virtualRow.index];
              const original = row.original;
              const selected = selectedRowId === row.id;
              return (
                <div
                  key={row.id}
                  role="button"
                  tabIndex={0}
                  data-testid="grid-row"
                  onClick={() => onSelectRow?.(original)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectRow?.(original);
                    }
                  }}
                  className={`pointer-events-auto absolute left-0 grid w-full min-w-max items-center border-b border-outline px-3 text-left text-sm transition ${
                    selected
                      ? "bg-primary/15 outline outline-1 outline-primary/40"
                      : "bg-background hover:bg-hover"
                  }`}
                  style={{
                    gridTemplateColumns: gridTemplate,
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                {visibleColumns.map((column) => {
                  const cell = row.getAllCells().find((c) => c.column.id === column.id);
                  if (!cell) return null;
                  return (
                    <div key={cell.id} className="min-w-0 truncate">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </div>
                  );
                })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      {footer}
    </section>
  );
}
