import type { ReviewRow, ReviewRowsQuery, ReviewStatus, ReviewRowType, ProposedAction } from "../types/review";
import type { QualityIssueType, QualityRow, QualityRowsQuery } from "../types/quality";
import { BridgeCallError } from "./bridgeErrors";

const FILE_NAMES = [
  "히어로는 악에게 패배하였습니다 1-1014 完.txt",
  "태초마을의 토끼 검사.txt",
  "절망과 좌절의 포인트.txt",
  "뉴토끼 백업본.txt",
  "마왕성의 회귀자.txt",
  "포인트 상점의 관리자.txt",
  "토끼 수인의 검술 교본.txt",
  "빙의자는 오늘도 살아남는다.txt",
];

const STATUSES: ReviewStatus[] = ["unreviewed", "approved", "conflict", "excluded"];
const TYPES: ReviewRowType[] = ["exact", "near", "relation", "move_only"];
const ACTIONS: ProposedAction[] = ["keep", "move_duplicate", "move_organized", "ignore"];
const TARGETS = ["duplicate/", "ㄱ-ㄴ/", "ㄷ-ㅁ/", "ㅂ-ㅅ/", "ㅇ-ㅈ/", "ㅋ-ㅎ/"];
const ENCODINGS = ["UTF-8", "CP949?", "Unknown", "UTF-8 BOM"];
const INTEGRITIES = ["OK", "Encoding warning", "Missing newline", "Read error"];

let cachedRows: ReviewRow[] | null = null;

export function getAllReviewRows(count = 1284): ReviewRow[] {
  if (cachedRows && cachedRows.length !== count) {
    cachedRows = null;
  }
  if (cachedRows) return cachedRows;

  cachedRows = Array.from({ length: count }, (_, index) => {
    // row-2: exact + move_duplicate for apply E2E (near rows are preview-blocked).
    const type = index === 1 ? "exact" : TYPES[index % TYPES.length];
    // row-6: encoding-only quality/repair parity (integrity OK, non–UTF-8).
    const integrity = index === 5 ? "OK" : INTEGRITIES[index % INTEGRITIES.length];
    const encoding = index === 5 ? "CP949?" : ENCODINGS[index % ENCODINGS.length];
    const status = STATUSES[index % STATUSES.length];
    const proposedAction = ACTIONS[index % ACTIONS.length];
    const groupId = type === "move_only" ? undefined : `group-${String((index % 37) + 1).padStart(2, "0")}`;

    return {
      id: `row-${index + 1}`,
      rowKind: index % 4 === 0 ? "group" : "file",
      status,
      type,
      name: FILE_NAMES[index % FILE_NAMES.length],
      keeperLabel: index % 3 === 0 ? "현재 파일" : FILE_NAMES[(index + 2) % FILE_NAMES.length],
      proposedAction,
      targetFolder: TARGETS[index % TARGETS.length],
      confidence: type === "move_only" ? undefined : 72 + (index % 25),
      sizeBytes: Math.round(((index % 27) + 1.3) * 1024 * 1024),
      encoding,
      integrity,
      hasChildren: index % 4 === 0,
      groupId,
      path: `/library/raw/${index + 1}/${FILE_NAMES[index % FILE_NAMES.length]}`,
    };
  });

  return cachedRows;
}

const QUALITY_SORT_FIELDS = new Set([
  "name",
  "path",
  "issueType",
  "severity",
  "encoding",
  "integrity",
]);

const SEVERITY_ORDINAL: Record<string, number> = { error: 0, warning: 1 };

export function textSortKey(value: string | null | undefined): string {
  return (value ?? "").normalize("NFC").toLocaleLowerCase("en-US");
}

export function sortQualityRows(
  rows: QualityRow[],
  sort?: QualityRowsQuery["sort"],
): QualityRow[] {
  if (!sort?.field) return rows;
  if (!QUALITY_SORT_FIELDS.has(sort.field)) {
    throw new BridgeCallError("Bridge call rejected: INVALID_SORT_FIELD", {
      code: "rejected",
      method: "queryQualityRows",
      reason: "INVALID_SORT_FIELD",
    });
  }
  const reverse = sort.direction === "desc";
  const field = sort.field;

  const indexed = rows.map((row, index) => ({ row, index }));
  const readField = (row: QualityRow): string | undefined => {
    if (field === "path") return row.path;
    if (field === "name") return row.name;
    if (field === "issueType") return row.issueType;
    if (field === "encoding") return row.encoding;
    if (field === "integrity") return row.integrity;
    return undefined;
  };

  indexed.sort((a, b) => {
    const cmp =
      field === "severity"
        ? -(SEVERITY_ORDINAL[a.row.severity] ?? 99) - -(SEVERITY_ORDINAL[b.row.severity] ?? 99)
        : textSortKey(readField(a.row)).localeCompare(textSortKey(readField(b.row)), "en-US");
    if (cmp !== 0) return reverse ? -cmp : cmp;
    if (a.index !== b.index) return a.index - b.index;
    return a.row.id.localeCompare(b.row.id);
  });
  return indexed.map((entry) => entry.row);
}

export function sortReviewRows(rows: ReviewRow[], sort?: ReviewRowsQuery["sort"]): ReviewRow[] {
  if (!sort?.field) return rows;
  const dir = sort.direction === "desc" ? -1 : 1;
  const field = sort.field as keyof ReviewRow;
  return [...rows].sort((a, b) => {
    const av = a[field];
    const bv = b[field];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv), "ko") * dir;
  });
}

export function filterReviewRows(rows: ReviewRow[], query: ReviewRowsQuery): ReviewRow[] {
  const search = query.filters?.search?.toLowerCase() ?? "";

  return rows.filter((row) => {
    if (query.viewMode === "conflicts" && row.status !== "conflict") return false;
    if (query.viewMode === "groups" && row.type === "move_only") return false;
    if (query.viewMode === "move") {
      if (row.rowKind !== "file") return false;
      if (row.status !== "approved") return false;
      if (row.proposedAction === "keep") return false;
    }
    if (query.viewMode === "action" && row.status !== "unreviewed" && row.status !== "conflict") {
      return false;
    }

    if (query.filters?.status?.length && !query.filters.status.includes(row.status)) {
      return false;
    }
    if (query.filters?.types?.length && !query.filters.types.includes(row.type)) {
      return false;
    }

    if (search) {
      const haystack = `${row.name} ${row.keeperLabel ?? ""} ${row.targetFolder ?? ""} ${row.type}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }

    return true;
  });
}

export function paginateRows<T>(rows: T[], cursor: string | null | undefined, limit = 100): {
  slice: T[];
  nextCursor: string | null;
  hasMore: boolean;
} {
  const offset = cursor ? Number.parseInt(cursor, 10) : 0;
  const safeOffset = Number.isFinite(offset) ? offset : 0;
  const slice = rows.slice(safeOffset, safeOffset + limit);
  const nextOffset = safeOffset + slice.length;
  const hasMore = nextOffset < rows.length;
  return {
    slice,
    nextCursor: hasMore ? String(nextOffset) : null,
    hasMore,
  };
}

export function buildQualityRows(): QualityRow[] {
  return getAllReviewRows()
    .filter((row) => row.integrity !== "OK" || row.encoding !== "UTF-8")
    .map((row, index) => {
      const issueType: QualityIssueType =
        row.integrity !== "OK" ? "integrity" : row.encoding !== "UTF-8" ? "encoding" : "small_file";
      const severity = row.integrity === "Read error" ? "error" : "warning";

      return {
        id: `quality-${index + 1}`,
        issueType,
        name: row.name,
        path: `D:/Novels/Library/raw/${index % 5 === 0 ? "fantasy" : "imported"}`,
        encoding: row.encoding,
        integrity: row.integrity ?? "OK",
        severity,
        suggestedAction: "v1: repair not available",
      };
    });
}

export function summarizeReviewRows(rows: ReviewRow[]) {
  return {
    selectedCount: 0,
    conflictCount: rows.filter((r) => r.status === "conflict").length,
    unreviewedCount: rows.filter((r) => r.status === "unreviewed").length,
    approvedCount: rows.filter((r) => r.status === "approved").length,
  };
}
