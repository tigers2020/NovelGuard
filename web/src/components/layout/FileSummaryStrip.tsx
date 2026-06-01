import type { AppSnapshot } from "../../types/snapshot";
import { formatBytes } from "../../lib/format";
import { StatChip } from "../ui/StatChip";

export function FileSummaryStrip({
  library,
  onOpenResolve,
}: {
  library: AppSnapshot["library"];
  onOpenResolve: () => void;
}) {
  return (
    <section className="shrink-0 border-t border-outline bg-surface px-5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-on-surface">
            {library.folderPath ?? "폴더 미선택"}
          </div>
          <div className="text-xs text-muted">
            Shell summary only · full review grid in 검토 · 정리
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatChip label="Files" value={library.fileCount.toLocaleString()} />
          <StatChip label="Size" value={formatBytes(library.totalBytes)} />
          <StatChip label="Dup groups" value={library.duplicateGroups} tone="warn" />
          <StatChip label="Integrity" value={library.integrityIssues} tone="danger" />
          <button
            type="button"
            onClick={onOpenResolve}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background hover:opacity-90"
          >
            검토 · 정리 열기
          </button>
        </div>
      </div>
    </section>
  );
}
