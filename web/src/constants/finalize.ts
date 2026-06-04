/** Bridge timeout for finalize re-verify (may reanalyze each quality-affected file). */
export function finalizeVerificationTimeoutMs(qualityReverifyFileCount: number): number {
  const n = Math.max(0, qualityReverifyFileCount);
  return Math.min(600_000, Math.max(120_000, 60_000 + n * 80));
}
