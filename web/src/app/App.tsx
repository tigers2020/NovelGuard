import { useCallback, useRef, useState, type ReactNode } from "react";
import { SnapshotProvider } from "./providers/SnapshotProvider";
import {
  useBridge,
  useBridgeHealth,
  useConnectionLabel,
  useSnapshot,
} from "./providers/snapshotHooks";
import { AppShell } from "../components/layout/AppShell";
import { AppHeader } from "../components/layout/AppHeader";
import { AppSidebar } from "../components/layout/AppSidebar";
import { ShellFileDock } from "../components/layout/ShellFileDock";
import {
  loadShellFileDockState,
  persistShellFileDockState,
} from "../components/layout/shellFileDockStorage";
import {
  persistFileDockCollapseForWorkMode,
  persistFileDockExpandForWorkMode,
  resolveInitialFileDockExpanded,
} from "../components/layout/shellFileDockModePolicy";
import { GlobalCommandBar } from "../components/layout/GlobalCommandBar";
import { LogsRoute } from "../features/logs/LogsRoute";
import { SettingsRoute } from "../features/settings/SettingsRoute";
import { WorkRoute } from "../features/work/WorkRoute";
import { ApplySubflowDialog } from "../features/work/ApplySubflowDialog";
import { FinalizeSubflowDialog } from "../features/work/FinalizeSubflowDialog";
import { PreflightPipelineDialog } from "../features/work/PreflightPipelineDialog";
import type { AppSnapshot, WorkMode } from "../types/snapshot";
import type { SelectionScope } from "../types/selection";

function AppContent() {
  const snapshot = useSnapshot();
  const bridge = useBridge();
  const bridgeHealth = useBridgeHealth();
  const connectionLabel = useConnectionLabel();
  const [route, setRoute] = useState<AppSnapshot["route"]>("work");
  const [preflightOpen, setPreflightOpen] = useState(false);
  const [pipelineOpen, setPipelineOpen] = useState(false);
  const [applyOpen, setApplyOpen] = useState(false);
  const [finalizeOpen, setFinalizeOpen] = useState(false);
  const [applySelection, setApplySelection] = useState<SelectionScope | null>(null);
  const [fileDockExpanded, setFileDockExpanded] = useState(() =>
    resolveInitialFileDockExpanded(snapshot.work.activeMode, snapshot.library.fileCount),
  );
  const requestWorkModeRef = useRef<((mode: WorkMode) => Promise<void>) | null>(null);

  const handleRequestWorkModeReady = useCallback((request: (mode: WorkMode) => Promise<void>) => {
    requestWorkModeRef.current = request;
  }, []);

  const requestWorkMode = useCallback(async (mode: WorkMode) => {
    setRoute("work");
    await requestWorkModeRef.current?.(mode);
  }, []);

  const applyFileDockPolicyForMode = useCallback(
    (mode: WorkMode) => {
      if (mode === "resolve" || mode === "quality") {
        persistFileDockCollapseForWorkMode(mode);
        setFileDockExpanded(false);
        return;
      }
      if (mode === "scan" && snapshot.library.fileCount > 0) {
        persistFileDockExpandForWorkMode(mode, snapshot.library.fileCount);
        setFileDockExpanded(true);
      }
    },
    [snapshot.library.fileCount],
  );

  const handleFullPipeline = () => {
    if (snapshot.work.resolve.hasPendingApply || snapshot.work.resolve.conflictCount > 0) {
      setPreflightOpen(true);
      return;
    }
    setPipelineOpen(true);
  };

  const handleOpenResolve = () => {
    void requestWorkMode("resolve");
  };

  const handleRevealFileDock = () => {
    setFileDockExpanded(true);
    persistShellFileDockState({ ...loadShellFileDockState(), expanded: true });
  };

  const handleFileDockExpandedChange = (next: boolean) => {
    setFileDockExpanded(next);
    persistShellFileDockState({ ...loadShellFileDockState(), expanded: next });
  };

  const handleOpenPreview = (selection: SelectionScope) => {
    setApplySelection(selection);
    setApplyOpen(true);
  };

  const workDockPrimary =
    route === "work" &&
    snapshot.work.activeMode === "scan" &&
    fileDockExpanded &&
    snapshot.library.fileCount > 0;

  let main: ReactNode;
  if (route === "work") {
    main = (
      <WorkRoute
        onOpenPreview={handleOpenPreview}
        onOpenFinalize={() => setFinalizeOpen(true)}
        onOpenSettings={() => setRoute("settings")}
        onRevealFileDock={handleRevealFileDock}
        onWorkModeApplied={applyFileDockPolicyForMode}
        onRequestWorkModeReady={handleRequestWorkModeReady}
        compactWorkChrome={workDockPrimary}
      />
    );
  } else if (route === "settings") {
    main = <SettingsRoute />;
  } else {
    main = <LogsRoute />;
  }

  return (
    <>
      <AppShell
        workDockPrimary={workDockPrimary}
        header={
          <AppHeader route={route} connection={connectionLabel} health={bridgeHealth} />
        }
        sidebar={<AppSidebar route={route} onRouteChange={setRoute} />}
        fileDock={
          <ShellFileDock
            expanded={fileDockExpanded}
            onExpandedChange={handleFileDockExpandedChange}
            preferFlexHeight={workDockPrimary}
          />
        }
        commandBar={
          <GlobalCommandBar
            pipeline={snapshot.pipeline}
            scan={snapshot.work.scan}
            onFullPipeline={handleFullPipeline}
            onCancel={() => void bridge.cancelRun()}
          />
        }
      >
        {main}
      </AppShell>

      <PreflightPipelineDialog
        open={preflightOpen}
        resolve={snapshot.work.resolve}
        onClose={() => setPreflightOpen(false)}
        onGoResolve={() => {
          setPreflightOpen(false);
          void handleOpenResolve();
        }}
        onContinue={() => {
          setPreflightOpen(false);
          setPipelineOpen(true);
        }}
      />

      {pipelineOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="max-w-md rounded-md border border-outline bg-surface p-5">
            <h2 className="text-lg font-bold text-on-surface">전체 파이프라인</h2>
            <p className="mt-2 text-sm text-on-surface-variant">
              scan → duplicate → move preview (subflow). v1 stub — pipeline state via mock bridge.
            </p>
            <button
              type="button"
              className="mt-4 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
              onClick={() => {
                void bridge.startScan();
                setPipelineOpen(false);
              }}
            >
              스캔 시작
            </button>
            <button
              type="button"
              className="ml-2 mt-4 rounded-md border border-outline px-3 py-2 text-sm"
              onClick={() => setPipelineOpen(false)}
            >
              닫기
            </button>
          </div>
        </div>
      )}

      <ApplySubflowDialog
        key={applyOpen ? "apply-open" : "apply-closed"}
        open={applyOpen}
        selection={applySelection}
        snapshotLibraryRevision={snapshot.work.resolve.libraryRevision}
        onOpenFinalize={() => setFinalizeOpen(true)}
        onClose={() => {
          setApplyOpen(false);
          setApplySelection(null);
        }}
      />
      <FinalizeSubflowDialog
        open={finalizeOpen}
        onClose={() => setFinalizeOpen(false)}
        onOpenLogs={() => {
          setFinalizeOpen(false);
          setRoute("logs");
        }}
      />
    </>
  );
}

export default function App() {
  return (
    <SnapshotProvider>
      <AppContent />
    </SnapshotProvider>
  );
}
