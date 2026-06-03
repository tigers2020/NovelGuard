import type { AppSnapshot } from "../../types/snapshot";
import type { BridgeHealth } from "../../bridge/bridgeHealth";

const routeLabels: Record<AppSnapshot["route"], string> = {
  work: "작업",
  settings: "설정",
  logs: "로그",
};

export function AppHeader({
  route,
  connection,
  health = "ok",
}: {
  route: AppSnapshot["route"];
  connection: string;
  health?: BridgeHealth;
}) {
  const tone =
    health === "ok"
      ? "border-success/30 bg-success/10 text-success"
      : health === "degraded"
        ? "border-secondary/30 bg-secondary/10 text-secondary"
        : "border-error/30 bg-error/10 text-error";

  const dotTone =
    health === "ok" ? "bg-success" : health === "degraded" ? "bg-secondary" : "bg-error";

  return (
    <header
      className="flex h-16 shrink-0 items-center justify-between border-b border-outline bg-surface-elevated/95 px-5 backdrop-blur"
      data-testid="app-header"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary font-bold text-background shadow">
          NG
        </div>
        <div>
          <div className="text-sm font-bold tracking-wide text-on-surface">NovelGuard</div>
          <div className="text-xs text-muted" data-testid="app-header-route">
            {routeLabels[route]}
          </div>
        </div>
      </div>
      <div
        className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${tone}`}
        data-testid="connection-badge"
      >
        <span className={`h-2 w-2 rounded-full ${dotTone}`} aria-hidden />
        {connection}
      </div>
    </header>
  );
}
