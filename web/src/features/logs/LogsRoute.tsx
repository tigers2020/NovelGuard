import { useCallback, useEffect, useMemo, useState } from "react";
import { useBridge } from "../../app/providers/snapshotHooks";
import { UI_FALLBACK } from "../../lib/uiFallbackCopy";
import type { LogEntry, LogLevel, LogsArtifactsResponse } from "../../types/logs";

export function LogsRoute() {
  const bridge = useBridge();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [artifacts, setArtifacts] = useState<LogsArtifactsResponse["artifacts"]>([]);
  const [level, setLevel] = useState<LogLevel | "">("");
  const [search, setSearch] = useState("");
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [displayCleared, setDisplayCleared] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    setDisplayCleared(false);
    try {
      const [logPage, artifactPage] = await Promise.all([
        bridge.queryLogEntries({ limit: 200, ...(level ? { level } : {}) }),
        bridge.getLogsArtifacts(),
      ]);
      setLogs(logPage.entries);
      setArtifacts(artifactPage.artifacts);
      setSelectedArtifactId((prev) =>
        prev && artifactPage.artifacts.some((item) => item.id === prev) ? prev : null,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : UI_FALLBACK.loadLogs);
    } finally {
      setLoading(false);
    }
  }, [bridge, level]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- bridge fetch on mount/level change
    void refresh();
  }, [refresh]);

  const visibleLogs: LogEntry[] = useMemo(() => {
    const base = displayCleared ? [] : logs;
    const needle = search.trim().toLowerCase();
    if (!needle) return base;
    return base.filter(
      (entry) =>
        entry.message.toLowerCase().includes(needle) ||
        entry.level.toLowerCase().includes(needle),
    );
  }, [displayCleared, logs, search]);

  const selectedArtifact = artifacts.find((item) => item.id === selectedArtifactId) ?? null;

  return (
    <div className="h-full overflow-y-auto bg-background p-6" data-testid="logs-route">
      <div className="rounded-md border border-outline bg-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-on-surface">로그</h1>
            <p className="mt-1 text-sm text-on-surface-variant">실행 로그 및 지원 산출물</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="search"
              data-testid="logs-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="메시지 검색…"
              className="min-w-[10rem] rounded-sm border border-outline bg-surface-elevated px-2 py-1 text-sm text-on-surface"
              aria-label="로그 메시지 검색"
            />
            <select
              className="rounded-sm border border-outline bg-surface-elevated px-2 py-1 text-sm text-on-surface"
              value={level}
              onChange={(event) => setLevel(event.target.value as LogLevel | "")}
              aria-label="로그 레벨 필터"
            >
              <option value="">전체</option>
              <option value="DEBUG">DEBUG+</option>
              <option value="INFO">INFO+</option>
              <option value="WARNING">WARNING+</option>
              <option value="ERROR">ERROR+</option>
            </select>
            <button
              type="button"
              className="rounded-sm border border-outline px-3 py-1 text-sm text-on-surface hover:bg-hover"
              onClick={() => void refresh()}
            >
              새로고침
            </button>
            <button
              type="button"
              className="rounded-sm border border-outline px-3 py-1 text-sm text-on-surface-variant hover:bg-hover"
              onClick={() => setDisplayCleared(true)}
            >
              화면 지우기
            </button>
          </div>
        </div>

        {error ? <p className="mt-3 text-sm text-error">{error}</p> : null}

        <section className="mt-6" data-testid="logs-live-list">
          <h2 className="text-sm font-semibold text-on-surface">실시간 로그</h2>
          {loading ? (
            <p className="mt-2 text-sm text-muted">불러오는 중…</p>
          ) : visibleLogs.length === 0 ? (
            <p className="mt-2 text-sm text-muted">표시할 로그가 없습니다.</p>
          ) : (
            <ul className="mt-2 max-h-96 space-y-1 overflow-y-auto font-mono text-xs">
              {visibleLogs.map((entry, index) => (
                <li key={`${entry.timestamp}-${index}`} className="text-on-surface-variant">
                  <span className="text-muted">{entry.timestamp}</span>{" "}
                  <span className="text-primary">[{entry.level}]</span> {entry.message}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-[1fr_minmax(12rem,0.4fr)]">
          <div data-testid="logs-artifacts-list">
            <h2 className="text-sm font-semibold text-on-surface">산출물</h2>
            {artifacts.length === 0 ? (
              <p className="mt-2 text-sm text-muted">등록된 산출물이 없습니다.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {artifacts.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      data-testid={`logs-artifact-${item.id}`}
                      onClick={() => setSelectedArtifactId(item.id)}
                      className={`w-full rounded-sm border px-3 py-2 text-left ${
                        selectedArtifactId === item.id
                          ? "border-primary bg-primary/10"
                          : "border-outline bg-surface-elevated hover:bg-hover"
                      }`}
                    >
                      <div className="text-sm font-medium text-on-surface">{item.label}</div>
                      <div className="truncate font-mono text-xs text-muted">{item.path}</div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <aside
            className="rounded-md border border-outline bg-surface-elevated p-3"
            data-testid="logs-artifact-detail"
          >
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">상세</h3>
            {selectedArtifact ? (
              <dl className="mt-2 space-y-2 text-sm">
                <div>
                  <dt className="text-muted">이름</dt>
                  <dd className="font-medium text-on-surface">{selectedArtifact.label}</dd>
                </div>
                <div>
                  <dt className="text-muted">종류</dt>
                  <dd className="text-on-surface-variant">{selectedArtifact.kind}</dd>
                </div>
                <div>
                  <dt className="text-muted">경로</dt>
                  <dd className="break-all font-mono text-xs text-on-surface-variant">
                    {selectedArtifact.path}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-2 text-sm text-muted">산출물을 선택하세요.</p>
            )}
          </aside>
        </section>
      </div>
    </div>
  );
}
