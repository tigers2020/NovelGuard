export function maxRenderedRowSlots({ overscan }: { overscan: number }): number {
  return overscan * 2 + 3;
}

export function isNearScrollEnd({
  scrollTop,
  clientHeight,
  scrollHeight,
  threshold,
}: {
  scrollTop: number;
  clientHeight: number;
  scrollHeight: number;
  threshold: number;
}): boolean {
  return scrollTop + clientHeight >= scrollHeight - threshold;
}

/** Gate for mock filter+paginate unit timing (see gridDataPath test). */
export function filterPaginateLatencyBudgetMs(): number {
  return 50;
}
