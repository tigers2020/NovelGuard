import type { Column } from "@tanstack/react-table";

export function parseRemWidthToPx(gridWidth: string): number | null {
  const match = /^([\d.]+)rem$/.exec(gridWidth.trim());
  if (!match) return null;
  return Math.round(parseFloat(match[1]) * 16);
}

export function defaultPxForGridWidth(gridWidth: string, minWidthPx = 48): number {
  return parseRemWidthToPx(gridWidth) ?? minWidthPx;
}

export function isFlexibleGridWidth(gridWidth: string): boolean {
  return gridWidth.includes("fr");
}

export function buildColumnGridTemplate<T>(
  columns: Column<T, unknown>[],
  sizing: Record<string, number>,
): string {
  return columns
    .map((col) => {
      const meta = col.columnDef.meta;
      const gridWidth = meta?.gridWidth ?? "minmax(0,1fr)";
      const customPx = sizing[col.id];

      if (isFlexibleGridWidth(gridWidth)) {
        if (customPx != null) return `minmax(${customPx}px, 1fr)`;
        return gridWidth;
      }
      if (customPx != null) return `${customPx}px`;
      return gridWidth;
    })
    .join(" ");
}

export function getColumnWidthPx<T>(
  column: Column<T, unknown>,
  sizing: Record<string, number>,
): number {
  const id = column.id;
  if (sizing[id] != null) return sizing[id];
  const gridWidth = column.columnDef.meta?.gridWidth ?? "minmax(0,1fr)";
  if (isFlexibleGridWidth(gridWidth)) {
    return column.columnDef.meta?.minWidthPx ?? 120;
  }
  return defaultPxForGridWidth(gridWidth, column.columnDef.meta?.minWidthPx ?? 48);
}
