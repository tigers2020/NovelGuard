import { useCallback, useEffect, useRef, useState } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import type { WorkMode } from "../../types/snapshot";
import type { SelectionScope } from "../../types/selection";
import { QualityWorkspace } from "./QualityWorkspace";
import { ResolveAndOrganizeWorkspace } from "./ResolveAndOrganizeWorkspace";
import { ScanWorkspace } from "./ScanWorkspace";
import { WorkModePanel } from "./WorkModePanel";
import { WorkModeTabs } from "./WorkModeTabs";

function workModeErrorMessage(err: unknown): string {
  if (err instanceof BridgeCallError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Work mode change failed";
}

export function WorkRoute({
  onOpenPreview,
  onOpenFinalize,
  onOpenSettings,
  onRevealFileDock,
  onWorkModeApplied,
  onRequestWorkModeReady,
  compactWorkChrome = false,
}: {
  onOpenPreview: (selection: SelectionScope) => void;
  onOpenFinalize: () => void;
  onOpenSettings: () => void;
  onRevealFileDock: () => void;
  onWorkModeApplied?: (mode: WorkMode) => void;
  /** Shell / dialog shortcuts must use the same sequenced mode handler as tabs. */
  onRequestWorkModeReady?: (request: (mode: WorkMode) => Promise<void>) => void;
  /** Scan + expanded FileDock: keep scan toolbar in document flow (not clipped). */
  compactWorkChrome?: boolean;
}) {
  const bridge = useBridge();
  const refreshSnapshot = useRefreshSnapshot();
  const snapshot = useSnapshot();
  const snapshotMode = snapshot.work.activeMode;
  const [optimisticMode, setOptimisticMode] = useState<WorkMode | null>(null);
  const [modeError, setModeError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);
  const pendingOptimistic =
    optimisticMode != null && snapshotMode !== optimisticMode ? optimisticMode : null;
  const displayMode = pendingOptimistic ?? snapshotMode;

  const requestWorkMode = useCallback(
    async (next: WorkMode) => {
      const seq = ++requestSeqRef.current;
      setModeError(null);
      setOptimisticMode(next);
      try {
        await bridge.setWorkMode(next);
        if (seq !== requestSeqRef.current) {
          return;
        }
        await refreshSnapshot();
        onWorkModeApplied?.(next);
      } catch (err) {
        if (seq !== requestSeqRef.current) {
          return;
        }
        setOptimisticMode(null);
        setModeError(workModeErrorMessage(err));
        await refreshSnapshot();
      }
    },
    [bridge, onWorkModeApplied, refreshSnapshot],
  );

  useEffect(() => {
    onRequestWorkModeReady?.(requestWorkMode);
  }, [onRequestWorkModeReady, requestWorkMode]);

  return (
    <div
      className={
        compactWorkChrome
          ? "flex flex-col overflow-hidden"
          : "flex h-full min-h-0 flex-col overflow-hidden"
      }
    >
      <WorkModeTabs mode={displayMode} onModeChange={(mode) => void requestWorkMode(mode)} />
      {modeError && (
        <p
          className="border-b border-error/40 bg-error/10 px-4 py-2 text-sm text-error"
          data-testid="work-mode-error"
          role="alert"
        >
          {modeError}
        </p>
      )}
      <div
        className={
          compactWorkChrome
            ? "shrink-0 overflow-hidden"
            : "relative min-h-0 min-w-0 flex-1 overflow-hidden"
        }
      >
        <WorkModePanel active={displayMode === "scan"} layout={compactWorkChrome ? "stacked" : "overlay"}>
          <ScanWorkspace
            library={snapshot.library}
            scan={snapshot.work.scan}
            quality={snapshot.work.quality}
            pipeline={snapshot.pipeline}
            onStartScan={() => void bridge.startScan()}
            onCancelScan={() => void bridge.cancelRun()}
            onOpenSettings={onOpenSettings}
            onRevealFileDock={onRevealFileDock}
          />
        </WorkModePanel>
        <WorkModePanel
          active={displayMode === "resolve"}
          layout={compactWorkChrome ? "stacked" : "overlay"}
        >
          <ResolveAndOrganizeWorkspace
            onOpenPreview={onOpenPreview}
            onOpenFinalize={onOpenFinalize}
          />
        </WorkModePanel>
        <WorkModePanel
          active={displayMode === "quality"}
          layout={compactWorkChrome ? "stacked" : "overlay"}
        >
          <QualityWorkspace onOpenFinalize={onOpenFinalize} />
        </WorkModePanel>
      </div>
    </div>
  );
}
