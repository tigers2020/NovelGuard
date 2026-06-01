import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import { mockBridge } from "../../bridge/mockBridge";
import { createPywebviewBridge, isPywebviewHost } from "../../bridge/pywebviewBridge";

const BridgeContext = createContext<NovelGuardBridge>(mockBridge);
const SnapshotContext = createContext<AppSnapshot | null>(null);

function resolveBridge(override?: NovelGuardBridge): NovelGuardBridge {
  if (override) return override;
  return isPywebviewHost() ? createPywebviewBridge() : mockBridge;
}

export function SnapshotProvider({
  children,
  bridge: bridgeOverride,
}: {
  children: ReactNode;
  bridge?: NovelGuardBridge;
}) {
  const [bridge] = useState(() => resolveBridge(bridgeOverride));
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const next = await bridge.getSnapshot();
      if (alive) setSnapshot(next);
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [bridge]);

  if (!snapshot) {
    return <div className="p-6 text-muted">Loading…</div>;
  }

  return (
    <BridgeContext.Provider value={bridge}>
      <SnapshotContext.Provider value={snapshot}>{children}</SnapshotContext.Provider>
    </BridgeContext.Provider>
  );
}

export function useBridge(): NovelGuardBridge {
  return useContext(BridgeContext);
}

export function useSnapshot(): AppSnapshot {
  const snapshot = useContext(SnapshotContext);
  if (!snapshot) {
    throw new Error("useSnapshot must be used within SnapshotProvider");
  }
  return snapshot;
}
