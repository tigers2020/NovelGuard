import { useCallback, useEffect, useState } from "react";
import { useBridge } from "../../app/providers/snapshotHooks";
import { AppInfoDiagnostics } from "../AppInfoDiagnostics";
import type { AppSettingKey, AppSettingValue } from "../../types/settings";

export function SettingsRoute() {
  const bridge = useBridge();
  const [extensionFilter, setExtensionFilter] = useState(".txt,.md");
  const [includeHidden, setIncludeHidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ext, hidden] = await Promise.all([
        bridge.getAppSetting("scan.extensionFilter"),
        bridge.getAppSetting("scan.includeHidden"),
      ]);
      setExtensionFilter(String(ext.value));
      setIncludeHidden(Boolean(hidden.value));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, [bridge]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- bridge hydration on mount
    void loadSettings();
  }, [loadSettings]);

  const persist = async (key: AppSettingKey, value: AppSettingValue) => {
    setError(null);
    try {
      await bridge.setAppSetting(key, value);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save setting");
      await loadSettings();
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-background p-6" data-testid="settings-route">
      <div className="rounded-md border border-outline bg-surface p-6">
        <h1 className="text-xl font-bold text-on-surface">설정</h1>
        <p className="mt-2 text-sm text-on-surface-variant">스캔 기본값 및 앱 정보</p>

        <section className="mt-6">
          <h2 className="text-sm font-semibold text-on-surface">스캔 기본값</h2>
          {loading ? (
            <p className="mt-2 text-sm text-muted">Loading…</p>
          ) : (
            <div className="mt-3 space-y-4">
              <label className="block">
                <span className="text-sm text-on-surface-variant">확장자 필터</span>
                <input
                  data-testid="settings-scan-extension"
                  className="mt-1 w-full rounded-sm border border-outline bg-surface-elevated px-3 py-2 text-sm text-on-surface"
                  value={extensionFilter}
                  onChange={(event) => setExtensionFilter(event.target.value)}
                  onBlur={() => void persist("scan.extensionFilter", extensionFilter)}
                />
              </label>
              <label className="flex items-center gap-2">
                <input
                  data-testid="settings-scan-subdirs"
                  type="checkbox"
                  checked
                  disabled
                  className="rounded-sm"
                />
                <span className="text-sm text-on-surface-variant">
                  하위 폴더 포함 — 현재는 항상 하위 폴더를 포함합니다
                </span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  data-testid="settings-scan-hidden"
                  type="checkbox"
                  checked={includeHidden}
                  onChange={(event) => {
                    const next = event.target.checked;
                    setIncludeHidden(next);
                    void persist("scan.includeHidden", next);
                  }}
                  className="rounded-sm"
                />
                <span className="text-sm text-on-surface">숨김 파일 포함</span>
              </label>
            </div>
          )}
          {error ? <p className="mt-2 text-sm text-error">{error}</p> : null}
        </section>

        <AppInfoDiagnostics />
      </div>
    </div>
  );
}
