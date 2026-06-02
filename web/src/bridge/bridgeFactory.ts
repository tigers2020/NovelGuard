import type { BridgeKind } from "./bridgeHealth";
import {
  BRIDGE_ERROR_CODES,
  BridgeUnavailableError,
} from "./bridgeErrors";
import type { NovelGuardBridge } from "./NovelGuardBridge";
import { mockBridge } from "./mockBridge";
import { createPywebviewBridge } from "./pywebviewBridge";

export type BridgeResolveEnv = {
  PROD: boolean;
  DEV: boolean;
  VITE_USE_MOCK_BRIDGE?: string;
};

export type PywebviewWindow = {
  pywebview?: {
    api?: Record<string, (...args: unknown[]) => Promise<unknown>>;
  };
};

export function resolveBridge(
  env: BridgeResolveEnv = import.meta.env,
  win: PywebviewWindow | undefined =
    typeof window !== "undefined" ? (window as PywebviewWindow) : undefined,
): { bridge: NovelGuardBridge; kind: BridgeKind } {
  const api = win?.pywebview?.api;

  if (api) {
    return { bridge: createPywebviewBridge(api), kind: "pywebview" };
  }

  if (env.PROD) {
    throw new BridgeUnavailableError(BRIDGE_ERROR_CODES.productionUnavailable);
  }

  if (env.VITE_USE_MOCK_BRIDGE === "true") {
    return { bridge: mockBridge, kind: "mock" };
  }

  throw new BridgeUnavailableError(BRIDGE_ERROR_CODES.devUnavailable);
}
