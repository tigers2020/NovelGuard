import { createContext } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import type { BridgeHealth, BridgeKind } from "../../bridge/bridgeHealth";
import { mockBridge } from "../../bridge/mockBridge";

export const BridgeContext = createContext<NovelGuardBridge>(mockBridge);
export const SnapshotContext = createContext<AppSnapshot | null>(null);
export const SnapshotRefreshContext = createContext<(() => Promise<void>) | null>(null);
export const HealthContext = createContext<BridgeHealth>("ok");
export const BridgeKindContext = createContext<BridgeKind>("mock");
