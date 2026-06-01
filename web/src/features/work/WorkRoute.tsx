import { useState } from "react";
import { useBridge, useSnapshot } from "../../app/providers/snapshotHooks";
import type { WorkMode } from "../../types/snapshot";
import type { SelectionScope } from "../../types/selection";
import { WorkModeTabs } from "./WorkModeTabs";
import { ScanWorkspace } from "./ScanWorkspace";
import { ResolveAndOrganizeWorkspace } from "./ResolveAndOrganizeWorkspace";
import { QualityWorkspace } from "./QualityWorkspace";

export function WorkRoute({ onOpenPreview }: { onOpenPreview: (selection: SelectionScope) => void }) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const snapshotMode = snapshot.work.activeMode;
  const [optimisticMode, setOptimisticMode] = useState<WorkMode | null>(null);
  const mode = optimisticMode ?? snapshotMode;

  const setModeOptimistic = async (next: WorkMode) => {
    setOptimisticMode(next);
    try {
      await bridge.setWorkMode(next);
    } finally {
      setOptimisticMode((current) => (current === next ? null : current));
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <WorkModeTabs mode={mode} onModeChange={(m) => void setModeOptimistic(m)} />
      <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
        {mode === "scan" && (
          <ScanWorkspace
            library={snapshot.library}
            scan={snapshot.work.scan}
            onStartScan={() => void bridge.startScan()}
            onGoResolve={() => void setModeOptimistic("resolve")}
          />
        )}
        {mode === "resolve" && <ResolveAndOrganizeWorkspace onOpenPreview={onOpenPreview} />}
        {mode === "quality" && <QualityWorkspace />}
      </div>
    </div>
  );
}
