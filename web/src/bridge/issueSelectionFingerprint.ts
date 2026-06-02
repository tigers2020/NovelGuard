import { sha256HexUtf8 } from "./selectionFingerprint";

function normalizeQualityIssueId(issueId: string): string | null {
  const trimmed = issueId.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("quality:")) {
    const payload = trimmed.slice("quality:".length);
    if (!payload || payload.startsWith("quality:")) return null;
    return `quality:${payload}`;
  }
  return `quality:${trimmed}`;
}

export function normalizeRepairIssueIds(issueIds: string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const raw of issueIds) {
    const resolved = normalizeQualityIssueId(raw);
    if (!resolved || seen.has(resolved)) continue;
    seen.add(resolved);
    normalized.push(resolved);
  }
  normalized.sort();
  return normalized;
}

export function issueSelectionFingerprint(issueIds: string[]): string {
  const normalized = normalizeRepairIssueIds(issueIds);
  return sha256HexUtf8(JSON.stringify({ issueIds: normalized }));
}
