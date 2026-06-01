export type BridgeKind = "mock" | "pywebview";

export type BridgeHealth = "ok" | "degraded" | "unavailable";

export function connectionLabel(
  kind: BridgeKind,
  health: BridgeHealth,
  detail?: string,
): string {
  if (kind === "mock") {
    return detail ?? "Mock bridge (browser dev)";
  }
  if (health === "ok") {
    return detail ?? "Bridge connected";
  }
  if (health === "degraded") {
    return detail ?? "Bridge degraded — retrying";
  }
  return detail ?? "Bridge unavailable";
}
