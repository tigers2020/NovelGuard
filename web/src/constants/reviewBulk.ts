/** Mirrors `MAX_REVIEW_MUTATIONS` in `src/application/review_decisions.py`. */
export const MAX_REVIEW_MUTATIONS = 500;

/** Mirrors `MAX_QUERY_LIMIT` in `src/app/selection_resolve.py` for `current_query` resolution. */
export const SELECTION_RESOLVE_ROW_CAP = 200;

export function bulkMutationTargetCount(filteredCount: number): number {
  return Math.min(Math.max(0, filteredCount), MAX_REVIEW_MUTATIONS);
}

/** Cursor offsets for chunked `current_query` review mutations (null = first page). */
export function bulkMutationChunkCursors(targetCount: number): (string | null)[] {
  const cursors: (string | null)[] = [];
  let offset = 0;
  while (offset < targetCount) {
    cursors.push(offset === 0 ? null : String(offset));
    offset += SELECTION_RESOLVE_ROW_CAP;
  }
  return cursors;
}
