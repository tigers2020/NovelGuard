import type {
  IssueEvidence,
  QualityIssueDetail,
  QualityIssueDetailResponse,
  QualityKind,
  QualityRow,
} from "../types/quality";

const NOT_FOUND_MESSAGE = "quality_issue_not_found" as const;

export function normalizeQualityIssueId(issueId: string): string | null {
  const trimmed = issueId.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("quality:")) {
    const payload = trimmed.slice("quality:".length);
    if (!payload || payload.startsWith("quality:")) {
      return null;
    }
    return `quality:${payload}`;
  }
  return `quality:${trimmed}`;
}

export function notFoundIdForRequest(issueId: string): string {
  const normalized = normalizeQualityIssueId(issueId);
  if (normalized !== null) {
    return normalized;
  }
  const trimmed = issueId.trim();
  if (trimmed.startsWith("quality:")) {
    return trimmed;
  }
  return trimmed ? `quality:${trimmed}` : "quality:";
}

function findQualityRow(issueId: string, rows: QualityRow[]): QualityRow | undefined {
  const normalized = normalizeQualityIssueId(issueId);
  if (normalized) {
    const hit = rows.find((r) => r.id === normalized);
    if (hit) {
      return hit;
    }
  }
  const trimmed = issueId.trim();
  return rows.find((r) => r.id === trimmed || r.id === issueId);
}

function kindForRow(row: QualityRow): QualityKind {
  if (row.issueType === "encoding") {
    return "invalid_utf8";
  }
  if (row.issueType === "small_file") {
    return row.integrity === "Empty file" ? "empty_file" : "tiny_file";
  }
  return "read_error";
}

function evidenceForRow(row: QualityRow, kind: QualityKind): IssueEvidence {
  const base = {
    message: row.integrity,
    severity: row.severity,
    sizeBytes: kind === "empty_file" ? 0 : 64,
  };
  if (kind === "empty_file") {
    return { kind, ...base, sizeBytes: 0 };
  }
  if (kind === "tiny_file") {
    return { kind, ...base, thresholdBytes: 128 };
  }
  if (kind === "invalid_utf8") {
    return { kind, ...base, decodeError: "invalid utf-8 sequence" };
  }
  return { kind, ...base, error: "mock read error" };
}

function repairEligibilityForKind(kind: QualityKind) {
  if (kind === "invalid_utf8") {
    return {
      eligible: false as const,
      reason: "repair_not_implemented" as const,
      futureAction: "utf8_convert" as const,
      label: "UTF-8 repair planned (PR-22)",
    };
  }
  if (kind === "read_error") {
    return {
      eligible: false as const,
      reason: "read_error" as const,
      label: "Cannot repair read errors automatically",
    };
  }
  return {
    eligible: false as const,
    reason: "issue_not_repairable" as const,
    label: "Manual review required",
  };
}

function buildOkDetail(row: QualityRow, libraryRevision: number): QualityIssueDetail {
  const kind = kindForRow(row);
  const id = row.id.startsWith("quality:") ? row.id : `quality:${row.id}`;
  return {
    id,
    libraryRevision,
    issueType: row.issueType,
    name: row.name,
    path: row.path ?? "",
    encoding: row.encoding ?? "Unknown",
    integrity: row.integrity,
    severity: row.severity,
    suggestedAction: row.suggestedAction ?? "Review manually",
    file: {
      fileId: `mock-file-${row.id}`,
      sizeBytes: kind === "empty_file" ? 0 : 64,
      modifiedAtNs: 1,
      extension: ".txt",
      contentSha256: "",
    },
    evidence: evidenceForRow(row, kind),
    repairEligibility: repairEligibilityForKind(kind),
  };
}

export function buildMockQualityIssueDetail(
  issueId: string,
  rows: QualityRow[],
  libraryRevision: number,
): QualityIssueDetailResponse {
  const normalized = normalizeQualityIssueId(issueId);
  if (normalized === null) {
    return {
      status: "not_found",
      id: notFoundIdForRequest(issueId),
      message: NOT_FOUND_MESSAGE,
    };
  }

  const row = findQualityRow(issueId, rows);
  if (!row) {
    return {
      status: "not_found",
      id: normalized,
      message: NOT_FOUND_MESSAGE,
    };
  }

  return {
    status: "ok",
    detail: buildOkDetail(row, libraryRevision),
  };
}
