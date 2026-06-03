import { useRef, useState } from "react";
import { useBridge, useRefreshSnapshot, useSnapshot } from "../../app/providers/snapshotHooks";
import { BridgeCallError } from "../../bridge/bridgeErrors";
import type { WorkMode } from "../../types/snapshot";
import type { SelectionScope } from "../../types/selection";
import { FinalizeWorkspace } from "./FinalizeWorkspace";
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

export function WorkRoute({ onOpenPreview }: { onOpenPreview: (selection: SelectionScope) => void }) {
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

  const requestWorkMode = async (next: WorkMode) => {
    const seq = ++requestSeqRef.current;
    setModeError(null);
    setOptimisticMode(next);
    try {
      await bridge.setWorkMode(next);
      if (seq !== requestSeqRef.current) {
        return;
      }
      await refreshSnapshot();
    } catch (err) {
      if (seq !== requestSeqRef.current) {
        return;
      }
      setOptimisticMode(null);
      setModeError(workModeErrorMessage(err));
      await refreshSnapshot();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
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
      <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
        <WorkModePanel active={displayMode === "scan"}>
          <ScanWorkspace
            library={snapshot.library}
            scan={snapshot.work.scan}
            onStartScan={() => void bridge.startScan()}
            onGoResolve={() => void requestWorkMode("resolve")}
          />
        </WorkModePanel>
        <WorkModePanel active={displayMode === "resolve"}>
          <ResolveAndOrganizeWorkspace onOpenPreview={onOpenPreview} />
        </WorkModePanel>
        <WorkModePanel active={displayMode === "quality"}>
          <QualityWorkspace />
        </WorkModePanel>
        <WorkModePanel active={displayMode === "finalize"}>
          <FinalizeWorkspace />
        </WorkModePanel>
      </div>
    </div>
  );
}
