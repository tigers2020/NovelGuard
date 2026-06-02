import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import type { BridgeHealth, BridgeKind } from "../../bridge/bridgeHealth";
import { getBridgeErrorCode } from "../../bridge/bridgeErrors";
import { resolveBridge } from "../../bridge/bridgeFactory";
import {
  BridgeContext,
  BridgeKindContext,
  HealthContext,
  SnapshotContext,
  SnapshotRefreshContext,
} from "./snapshotContexts";
import { createTestBridge, readTestBridgeFailMode } from "../../bridge/testBridge";

type BridgeSelection =
  | { status: "ok"; bridge: NovelGuardBridge; kind: BridgeKind }
  | { status: "unavailable"; unavailableCode: string };

function selectBridge(override?: NovelGuardBridge): BridgeSelection {
  if (override) {
    return { status: "ok", bridge: override, kind: "mock" };
  }

  const failMode = readTestBridgeFailMode();
  if (failMode !== "none") {
    return { status: "ok", bridge: createTestBridge(failMode), kind: "mock" };
  }

  try {
    const resolved = resolveBridge();
    return { status: "ok", bridge: resolved.bridge, kind: resolved.kind };
  } catch (error) {
    return { status: "unavailable", unavailableCode: getBridgeErrorCode(error) };
  }
}

function BridgeUnavailableScreen({ code }: { code: string }) {
  return (
    <HealthContext.Provider value="unavailable">
      <BridgeKindContext.Provider value="pywebview">
        <div className="p-6 text-error" data-testid="bridge-unavailable">
          Bridge unavailable. {code}
        </div>
      </BridgeKindContext.Provider>
    </HealthContext.Provider>
  );
}

export function SnapshotProvider({
  children,
  bridge: bridgeOverride,
}: {
  children: ReactNode;
  bridge?: NovelGuardBridge;
}) {
  const [selection] = useState(() => selectBridge(bridgeOverride));

  if (selection.status === "unavailable") {
    return <BridgeUnavailableScreen code={selection.unavailableCode} />;
  }

  return (
    <SnapshotProviderInner bridge={selection.bridge} kind={selection.kind}>
      {children}
    </SnapshotProviderInner>
  );
}

function SnapshotProviderInner({
  children,
  bridge,
  kind,
}: {
  children: ReactNode;
  bridge: NovelGuardBridge;
  kind: BridgeKind;
}) {
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [health, setHealth] = useState<BridgeHealth>("ok");
  const [connectionDetail, setConnectionDetail] = useState<string | undefined>(undefined);

  const refreshSnapshot = useCallback(async () => {
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
  }, [bridge]);

  useEffect(() => {
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
  }, [refreshSnapshot]);

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
