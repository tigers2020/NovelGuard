import { useEffect, useState } from "react";
import { useBridge } from "../app/providers/snapshotHooks";
import type { AppInfo } from "../types/appInfo";

export function AppInfoDiagnostics() {
  const bridge = useBridge();
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void bridge
      .getAppInfo()
      .then((payload) => {
        if (alive) {
          setInfo(payload);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (alive) {
          setError(err instanceof Error ? err.message : "getAppInfo failed");
        }
      });
    return () => {
      alive = false;
    };
  }, [bridge]);

  return (
    <section className="mt-6 border-t border-outline pt-4" data-testid="app-info-diagnostics">
      <h2 className="text-sm font-semibold text-on-surface">앱 정보</h2>
      {error ? (
        <p className="mt-1 text-sm text-error">{error}</p>
      ) : info ? (
        <p className="mt-1 text-sm text-on-surface-variant">
          {info.appName} {info.version} · {info.buildType} · Python {info.pythonRuntime}
        </p>
      ) : (
        <p className="mt-1 text-sm text-muted">Loading…</p>
      )}
    </section>
  );
}
