import { useRef, type ReactNode } from "react";
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
  estimateRowHeight = 48,
  overscan = 8,
  onNearEnd,
  footer,
  testId,
  headerTestIdPrefix = "grid-header",
}: VirtualizedDataGridProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

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

  const gridTemplate = table
    .getVisibleLeafColumns()
    .map((col) => col.columnDef.meta?.gridWidth ?? "minmax(0,1fr)")
    .join(" ");

  return (
    <section
      data-testid={testId}
      className="flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden border-r border-outline bg-background"
    >
      <div className="overflow-x-auto border-b border-outline bg-surface">
        <div
          className="grid min-w-max px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
          style={{ gridTemplateColumns: gridTemplate }}
        >
        {table.getHeaderGroups().map((hg) =>
          hg.headers.map((header) => {
            const canSort = header.column.getCanSort();
            const sorted = header.column.getIsSorted();
            return (
              <button
                key={header.id}
                type="button"
                data-testid={`${headerTestIdPrefix}-${header.id}`}
                disabled={!canSort}
                onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                className={`truncate text-left ${canSort ? "cursor-pointer hover:text-on-surface" : "cursor-default"}`}
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
                {sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : null}
              </button>
            );
          }),
        )}
        </div>
      </div>
      <div ref={parentRef} className="min-h-0 flex-1 overflow-auto" onScroll={handleScroll}>
        <div className="relative w-full" style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
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
                className={`absolute left-0 grid w-full items-center border-b border-outline px-3 text-left text-sm transition ${
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
                {row.getVisibleCells().map((cell) => (
                  <div key={cell.id} className="min-w-0 truncate">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
      {footer}
    </section>
  );
}
