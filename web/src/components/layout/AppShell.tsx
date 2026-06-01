import type { ReactNode } from "react";

export function AppShell({
  header,
  sidebar,
  children,
  strip,
  commandBar,
}: {
  header: ReactNode;
  sidebar: ReactNode;
  children: ReactNode;
  strip: ReactNode;
  commandBar: ReactNode;
}) {
  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-on-surface">
      <div className="shrink-0">{header}</div>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="w-56 shrink-0 overflow-hidden">{sidebar}</div>
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">{children}</main>
      </div>
      <div className="shrink-0">{strip}</div>
      <div className="shrink-0">{commandBar}</div>
    </div>
  );
}
