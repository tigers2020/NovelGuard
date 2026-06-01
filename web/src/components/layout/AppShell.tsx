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
    <div className="grid h-full min-h-full grid-rows-[auto_1fr_auto_auto] overflow-hidden bg-background text-on-surface">
      {header}
      <div className="grid min-h-0 grid-cols-[14rem_1fr]">
        {sidebar}
        <main className="min-h-0 min-w-0 overflow-hidden">{children}</main>
      </div>
      {strip}
      {commandBar}
    </div>
  );
}
