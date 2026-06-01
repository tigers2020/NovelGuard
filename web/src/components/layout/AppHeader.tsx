import type { AppSnapshot } from "../../types/snapshot";

const routeLabels: Record<AppSnapshot["route"], string> = {
  work: "작업",
  settings: "설정",
  logs: "로그",
};

export function AppHeader({
  route,
  connection,
}: {
  route: AppSnapshot["route"];
  connection: string;
}) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-outline bg-surface-elevated/95 px-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary font-bold text-background shadow">
          NG
        </div>
        <div>
          <div className="text-sm font-bold tracking-wide text-on-surface">NovelGuard</div>
          <div className="text-xs text-muted">{routeLabels[route]}</div>
        </div>
      </div>
      <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 text-xs font-medium text-success">
        <span className="h-2 w-2 rounded-full bg-success" aria-hidden />
        {connection}
      </div>
    </header>
  );
}
