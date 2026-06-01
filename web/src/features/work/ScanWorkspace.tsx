import type { AppSnapshot } from "../../types/snapshot";
import { formatBytes } from "../../lib/format";
import { StatChip } from "../../components/ui/StatChip";

export function ScanWorkspace({
  library,
  scan,
  onStartScan,
  onGoResolve,
}: {
  library: AppSnapshot["library"];
  scan: AppSnapshot["work"]["scan"];
  onStartScan: () => void;
  onGoResolve: () => void;
}) {
  return (
    <main className="h-full overflow-y-auto bg-background p-5">
      <div className="mx-auto max-w-6xl space-y-4">
        <section className="rounded-md border border-outline bg-surface p-5">
          <p className="text-xs font-semibold text-secondary">Scan / Import</p>
          <h1 className="mt-1 text-2xl font-bold text-on-surface">라이브러리 인덱싱</h1>
          <p className="mt-2 max-w-2xl text-sm text-on-surface-variant">
            스캔은 데이터 준비 단계입니다. 수백~수천 파일 검토는 검토 · 정리에서 처리합니다.
          </p>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-md border border-outline bg-surface p-5">
            <h2 className="text-lg font-bold text-on-surface">대상 폴더</h2>
            <p className="mt-4 rounded-md border border-outline bg-background p-4 text-sm text-on-surface-variant">
              {library.folderPath ?? "—"}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {library.scanOptions.map((option) => (
                <span
                  key={option}
                  className="rounded-full border border-outline bg-background px-3 py-1 text-xs text-on-surface-variant"
                >
                  {option}
                </span>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onStartScan}
                className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-background hover:opacity-90"
              >
                스캔 시작
              </button>
            </div>
            <p className="mt-2 text-xs text-muted">상태: {scan.state}</p>
          </div>

          <div className="rounded-md border border-outline bg-surface p-5">
            <h2 className="text-lg font-bold text-on-surface">스캔 결과 요약</h2>
            <div className="mt-4 grid gap-3">
              <StatChip label="Files" value={library.fileCount.toLocaleString()} />
              <StatChip label="Size" value={formatBytes(library.totalBytes)} />
              <StatChip label="Last run" value={scan.lastRun ?? "—"} />
            </div>
            <button
              type="button"
              onClick={onGoResolve}
              className="mt-5 w-full rounded-md border border-outline bg-hover px-4 py-2 text-sm font-semibold text-on-surface"
            >
              검토 · 정리로 이동
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
