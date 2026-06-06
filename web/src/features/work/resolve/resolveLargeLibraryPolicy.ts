export const LARGE_LIBRARY_THRESHOLD = 500;

/** Large review sets load first page only on mount; smaller sets may load all filtered rows. */
export function shouldLoadFirstPageOnly(totalFiltered: number): boolean {
  return totalFiltered > LARGE_LIBRARY_THRESHOLD;
}
