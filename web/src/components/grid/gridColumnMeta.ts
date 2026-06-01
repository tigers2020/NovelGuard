import "@tanstack/react-table";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    gridWidth?: string;
    /** Minimum width (px) when column resize is enabled. */
    minWidthPx?: number;
    /** Show drag handle on header; defaults to true for fixed-width columns. */
    resizable?: boolean;
  }
}
