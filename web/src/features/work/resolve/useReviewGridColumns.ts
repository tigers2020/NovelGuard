import { useEffect, useState, type RefObject } from "react";

export type ReviewGridColumns = {
  status: boolean;
  type: boolean;
  action: boolean;
  target: boolean;
  conf: boolean;
};

const COLUMN_WIDTHS = {
  status: "5rem",
  type: "5rem",
  action: "7rem",
  target: "7rem",
  conf: "4.5rem",
} as const;

function columnsForWidth(width: number): ReviewGridColumns {
  return {
    status: width >= 300,
    type: width >= 300,
    action: width >= 400,
    target: width >= 500,
    conf: width >= 600,
  };
}

export function gridTemplateForColumns(cols: ReviewGridColumns): string {
  const parts: string[] = [];
  if (cols.status) parts.push(COLUMN_WIDTHS.status);
  if (cols.type) parts.push(COLUMN_WIDTHS.type);
  parts.push("minmax(0, 1fr)");
  if (cols.action) parts.push(COLUMN_WIDTHS.action);
  if (cols.target) parts.push(COLUMN_WIDTHS.target);
  if (cols.conf) parts.push(COLUMN_WIDTHS.conf);
  return parts.join(" ");
}

export function useReviewGridColumns(
  containerRef: RefObject<HTMLElement | null>,
): ReviewGridColumns {
  const [columns, setColumns] = useState<ReviewGridColumns>(() =>
    columnsForWidth(800),
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = (width: number) => setColumns(columnsForWidth(width));
    update(el.clientWidth);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      update(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [containerRef]);

  return columns;
}
