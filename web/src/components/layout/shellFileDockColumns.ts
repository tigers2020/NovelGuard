import type { FileRow, FileRowColumnPreset, FileRowSortField } from "../../types/fileRows";
import { formatBytes } from "../../lib/format";

export type ShellFileDockColumn = {
  id: string;
  header: string;
  cell: (row: FileRow) => string;
  sortField?: FileRowSortField;
};

export function columnsForPreset(preset: FileRowColumnPreset): ShellFileDockColumn[] {
  if (preset === "technical") {
    return [
      { id: "name", header: "파일명", cell: (r) => r.name, sortField: "name" },
      { id: "path", header: "경로", cell: (r) => r.path, sortField: "path" },
      { id: "extension", header: "확장자", cell: (r) => r.extension ?? "—", sortField: "extension" },
      {
        id: "encoding",
        header: "인코딩",
        cell: (r) => r.integrityStatus ?? "—",
        sortField: "encoding",
      },
      { id: "attributes", header: "속성", cell: () => "—" },
      {
        id: "modified",
        header: "수정일",
        cell: (r) => r.modifiedAt ?? "—",
        sortField: "modifiedAt",
      },
    ];
  }
  if (preset === "review") {
    return [
      { id: "name", header: "파일명", cell: (r) => r.name, sortField: "name" },
      {
        id: "size",
        header: "크기",
        cell: (r) => (r.sizeBytes != null ? formatBytes(r.sizeBytes) : "—"),
        sortField: "size",
      },
      {
        id: "dup",
        header: "중복 그룹",
        cell: (r) => r.duplicateGroupId ?? "—",
        sortField: "duplicateGroup",
      },
      { id: "keeper", header: "대표", cell: (r) => (r.isKeeper ? "대표" : "—") },
      {
        id: "integrity",
        header: "무결성",
        cell: (r) => r.integrityStatus ?? "—",
        sortField: "integrity",
      },
    ];
  }
  return [
    { id: "name", header: "파일명", cell: (r) => r.name, sortField: "name" },
    { id: "path", header: "경로", cell: (r) => r.path, sortField: "path" },
    {
      id: "size",
      header: "크기",
      cell: (r) => (r.sizeBytes != null ? formatBytes(r.sizeBytes) : "—"),
      sortField: "size",
    },
    {
      id: "modified",
      header: "수정일",
      cell: (r) => r.modifiedAt ?? "—",
      sortField: "modifiedAt",
    },
  ];
}
