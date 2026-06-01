import { useCallback, useEffect, useRef, useState } from "react";
import { useBridge, useSnapshot } from "../../app/providers/snapshotHooks";
import type { QualityIssueDetail, QualityIssueType, QualityRow } from "../../types/quality";
import { StatChip } from "../../components/ui/StatChip";
import { QualityIssueGrid } from "./quality/QualityIssueGrid";

const issueTabs: { id: QualityIssueType; label: string }[] = [
  { id: "integrity", label: "무결성" },
  { id: "encoding", label: "인코딩" },
  { id: "small_file", label: "소형 파일" },
];

export function QualityWorkspace() {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const quality = snapshot.work.quality;

  const [issueType, setIssueType] = useState<QualityIssueType>("integrity");
  const [rows, setRows] = useState<QualityRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [selected, setSelected] = useState<QualityRow | null>(null);
  const [detail, setDetail] = useState<QualityIssueDetail | null>(null);

  const loadDetail = useCallback(
    (row: QualityRow | null) => {
      if (!row) {
        setDetail(null);
        return;
      }
      void bridge.getQualityIssueDetail(row.id).then(setDetail);
    },
    [bridge],
  );

  const loadPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (append) setLoadingMore(true);
      try {
        setQueryError(null);
        const page = await bridge.queryQualityRows({ issueType, cursor, limit: 100 });
        setNextCursor(page.pageInfo.nextCursor);
        setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
        if (!append) {
          const first = page.rows[0] ?? null;
          setSelected(first);
          loadDetail(first);
        }
      } catch (err) {
        setQueryError(err instanceof Error ? err.message : "Failed to load quality rows");
        if (!append) {
          setRows([]);
          setNextCursor(null);
        }
      } finally {
        setLoadingMore(false);
      }
    },
    [bridge, issueType, loadDetail],
  );

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      void loadPage(null, false);
    });
    return () => cancelAnimationFrame(frame);
  }, [loadPage]);

  const loadingMoreRef = useRef(false);
  const handleNearEnd = () => {
    if (!nextCursor || loadingMore || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    void loadPage(nextCursor, true).finally(() => {
      loadingMoreRef.current = false;
    });
  };

  const handleSelect = (row: QualityRow) => {
    setSelected(row);
    loadDetail(row);
  };

  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-background p-5">
      <section className="shrink-0 rounded-md border border-outline bg-surface p-5">
        <h1 className="text-xl font-bold text-on-surface">품질 · 무결성</h1>
        <p className="mt-1 text-sm text-on-surface-variant">v1: read-only issue list · repair stub</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <StatChip label="Integrity" value={quality.integrityIssueCount} tone="danger" />
          <StatChip label="Encoding" value={quality.encodingIssueCount} tone="warn" />
          <StatChip label="Small files" value={quality.smallFileAnomalyCount} />
        </div>
        <div className="mt-4 flex gap-2">
          {issueTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setIssueType(tab.id)}
              className={`rounded-md px-3 py-2 text-sm font-semibold ${
                issueType === tab.id
                  ? "bg-primary text-background"
                  : "border border-outline text-on-surface-variant hover:bg-hover"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {queryError && (
          <p className="mt-2 text-sm text-error" data-testid="quality-query-error">
            {queryError}
          </p>
        )}
      </section>

      <div className="mt-4 grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_280px]">
        <QualityIssueGrid
          rows={rows}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onNearEnd={handleNearEnd}
          loadingMore={loadingMore}
        />
        <aside className="overflow-y-auto rounded-md border border-outline bg-surface p-4 text-sm">
          <p className="font-semibold text-on-surface">Issue detail</p>
          {detail ? (
            <dl className="mt-3 space-y-2">
              <div>
                <dt className="text-muted">Name</dt>
                <dd>{detail.name}</dd>
              </div>
              <div>
                <dt className="text-muted">Path</dt>
                <dd className="break-all">{detail.path}</dd>
              </div>
              <div>
                <dt className="text-muted">Suggested</dt>
                <dd>{selected?.suggestedAction}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-muted">행을 선택하세요.</p>
          )}
        </aside>
      </div>
    </main>
  );
}
