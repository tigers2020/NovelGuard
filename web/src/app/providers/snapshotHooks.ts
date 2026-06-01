import { useContext } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import { connectionLabel, type BridgeHealth, type BridgeKind } from "../../bridge/bridgeHealth";
import {
  BridgeContext,
  BridgeKindContext,
  HealthContext,
  SnapshotContext,
} from "./snapshotContexts";

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

export function useBridgeHealth(): BridgeHealth {
  return useContext(HealthContext);
}

export function useBridgeKind(): BridgeKind {
  return useContext(BridgeKindContext);
}

export function useConnectionLabel(): string {
  const snapshot = useContext(SnapshotContext);
  const health = useBridgeHealth();
  const kind = useBridgeKind();
  if (!snapshot) {
    return connectionLabel(kind, health);
  }
  return connectionLabel(kind, health, snapshot.connection);
}
