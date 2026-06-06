/** FileDock keeps loaded rows when bridge read times out after retries. */
export function shouldClearRowsOnFetchFailure(timedOut: boolean, append: boolean): boolean {
  if (timedOut) return false;
  return !append;
}
