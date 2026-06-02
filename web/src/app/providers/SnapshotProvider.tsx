import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import type { BridgeHealth, BridgeKind } from "../../bridge/bridgeHealth";
import { mockBridge } from "../../bridge/mockBridge";
import {
  BridgeContext,
  BridgeKindContext,
  HealthContext,
  SnapshotContext,
  SnapshotRefreshContext,
} from "./snapshotContexts";
import {
  createPywebviewBridge,
  getPywebviewApi,
  getPywebviewState,
} from "../../bridge/pywebviewBridge";
import { createTestBridge, readTestBridgeFailMode } from "../../bridge/testBridge";

function resolveBridge(override?: NovelGuardBridge): { bridge: NovelGuardBridge; kind: BridgeKind } {
  if (override) {
    return { bridge: override, kind: "mock" };
  }

  const failMode = readTestBridgeFailMode();
  if (failMode !== "none") {
    return { bridge: createTestBridge(failMode), kind: "mock" };
  }

  const api = getPywebviewApi();
  if (api) {
    return { bridge: createPywebviewBridge(api), kind: "pywebview" };
  }

  return { bridge: mockBridge, kind: "mock" };
}

export function SnapshotProvider({
  children,
  bridge: bridgeOverride,
}: {
  children: ReactNode;
  bridge?: NovelGuardBridge;
}) {
  const pyState = useMemo(() => getPywebviewState(), []);
  const [{ bridge, kind }] = useState(() => resolveBridge(bridgeOverride));
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [health, setHealth] = useState<BridgeHealth>(pyState === "broken" ? "unavailable" : "ok");
  const [connectionDetail, setConnectionDetail] = useState<string | undefined>(
    pyState === "broken" ? "pywebview.api is missing" : undefined,
  );

  const refreshSnapshot = useCallback(async () => {
    if (pyState === "broken") {
      return;
    }
    try {
      const next = await bridge.getSnapshot();
      setSnapshot(next);
      setHealth("ok");
      setConnectionDetail(undefined);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Snapshot failed";
      setHealth("degraded");
      setConnectionDetail(message);
    }
  }, [bridge, pyState]);

  useEffect(() => {
    if (pyState === "broken") {
      return;
    }

    let alive = true;

    const tick = async () => {
      if (!alive) {
        return;
      }
      await refreshSnapshot();
    };

    void tick();
    const id = window.setInterval(() => void tick(), 1000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [pyState, refreshSnapshot]);

  if (pyState === "broken") {
    return (
      <HealthContext.Provider value="unavailable">
        <BridgeKindContext.Provider value="pywebview">
          <div className="p-6 text-error" data-testid="bridge-unavailable">
            Bridge unavailable. {connectionDetail}
          </div>
        </BridgeKindContext.Provider>
      </HealthContext.Provider>
    );
  }

  if (!snapshot && health !== "ok") {
    return (
      <HealthContext.Provider value={health}>
        <BridgeKindContext.Provider value={kind}>
          <div className="p-6 text-error" data-testid="bridge-unavailable">
            Bridge unavailable. {connectionDetail ?? "Could not load snapshot"}
          </div>
        </BridgeKindContext.Provider>
      </HealthContext.Provider>
    );
  }

  if (!snapshot) {
    return <div className="p-6 text-muted">Loading…</div>;
  }

  return (
    <BridgeContext.Provider value={bridge}>
      <SnapshotRefreshContext.Provider value={refreshSnapshot}>
        <SnapshotContext.Provider value={snapshot}>
          <HealthContext.Provider value={health}>
            <BridgeKindContext.Provider value={kind}>{children}</BridgeKindContext.Provider>
          </HealthContext.Provider>
        </SnapshotContext.Provider>
      </SnapshotRefreshContext.Provider>
    </BridgeContext.Provider>
  );
}
