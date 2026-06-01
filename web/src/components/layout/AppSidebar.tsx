import type { AppSnapshot } from "../../types/snapshot";

const nav: { id: AppSnapshot["route"]; label: string }[] = [
  { id: "work", label: "작업" },
  { id: "settings", label: "설정" },
  { id: "logs", label: "로그" },
];

export function AppSidebar({
  route,
  onRouteChange,
}: {
  route: AppSnapshot["route"];
  onRouteChange: (route: AppSnapshot["route"]) => void;
}) {
  return (
    <aside className="shrink-0 border-r border-outline bg-surface p-3">
      <div className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-muted">Navigation</div>
      <nav className="space-y-1">
        {nav.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`nav-${item.id}`}
            onClick={() => onRouteChange(item.id)}
            className={`flex w-full items-center rounded-md px-3 py-2.5 text-left text-sm font-semibold transition ${
              route === item.id
                ? "bg-primary text-background"
                : "text-on-surface-variant hover:bg-hover"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
