import type { FileRow, FileRowColumnPreset } from "../../types/fileRows";
import { formatBytes } from "../../lib/format";

export type ShellFileDockColumn = {
  id: string;
  header: string;
  cell: (row: FileRow) => string;
};

export function columnsForPreset(preset: FileRowColumnPreset): ShellFileDockColumn[] {
  if (preset === "review") {
    return [
      { id: "name", header: "파일명", cell: (r) => r.name },
      {
        id: "size",
        header: "크기",
        cell: (r) => (r.sizeBytes != null ? formatBytes(r.sizeBytes) : "—"),
      },
      {
        id: "dup",
        header: "중복 그룹",
        cell: (r) => r.duplicateGroupId ?? "—",
      },
      {
        id: "keeper", header: "대표", cell: (r) => (r.isKeeper ? "대표" : "—") },
      { id: "integrity", header: "무결성", cell: (r) => r.integrityStatus ?? "—" },
    ];
  }
  return [
    { id: "name", header: "파일명", cell: (r) => r.name },
    { id: "path", header: "경로", cell: (r) => r.path },
    {
      id: "size",
      header: "크기",
      cell: (r) => (r.sizeBytes != null ? formatBytes(r.sizeBytes) : "—"),
    },
    { id: "modified", header: "수정일", cell: (r) => r.modifiedAt ?? "—" },
  ];
}
