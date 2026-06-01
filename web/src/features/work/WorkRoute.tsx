import { useBridge, useSnapshot } from "../../app/providers/SnapshotProvider";
import type { SelectionScope } from "../../types/selection";
import { WorkModeTabs } from "./WorkModeTabs";
import { ScanWorkspace } from "./ScanWorkspace";
import { ResolveAndOrganizeWorkspace } from "./ResolveAndOrganizeWorkspace";
import { QualityWorkspace } from "./QualityWorkspace";

export function WorkRoute({ onOpenPreview }: { onOpenPreview: (selection: SelectionScope) => void }) {
  const bridge = useBridge();
  const snapshot = useSnapshot();
  const mode = snapshot.work.activeMode;

  const setMode = async (next: typeof mode) => {
    await bridge.setWorkMode(next);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <WorkModeTabs mode={mode} onModeChange={(m) => void setMode(m)} />
      <div className="min-h-0 flex-1">
        {mode === "scan" && (
          <ScanWorkspace
            library={snapshot.library}
            scan={snapshot.work.scan}
            onStartScan={() => void bridge.startScan()}
            onGoResolve={() => void setMode("resolve")}
          />
        )}
        {mode === "resolve" && <ResolveAndOrganizeWorkspace onOpenPreview={onOpenPreview} />}
        {mode === "quality" && <QualityWorkspace />}
      </div>
    </div>
  );
}
