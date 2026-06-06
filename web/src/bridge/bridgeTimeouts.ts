const BRIDGE_TIMEOUT_MS: Record<string, number> = {
  get_snapshot: 5_000,
  query_file_rows: 60_000,
  query_review_rows: 45_000,
  query_quality_rows: 45_000,
  start_scan: 10_000,
  get_move_preview: 120_000,
};

const DEFAULT_TIMEOUT_MS = 15_000;

export function getBridgeTimeoutMs(method: string): number {
  return BRIDGE_TIMEOUT_MS[method] ?? DEFAULT_TIMEOUT_MS;
}
