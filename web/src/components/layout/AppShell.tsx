import type { ReactNode } from "react";

export function AppShell({
  header,
  sidebar,
  children,
  fileDock,
  commandBar,
  workDockPrimary = false,
}: {
  header: ReactNode;
  sidebar: ReactNode;
  children: ReactNode;
  fileDock: ReactNode;
  commandBar: ReactNode;
  /** Scan mode: compact work header + FileDock fills remaining main height. */
  workDockPrimary?: boolean;
}) {
  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-on-surface">
      <div className="shrink-0">{header}</div>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="w-56 shrink-0 overflow-hidden">{sidebar}</div>
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {workDockPrimary ? (
            <>
              <div className="shrink-0 overflow-hidden">{children}</div>
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{fileDock}</div>
            </>
          ) : (
            <>
              <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
              {fileDock}
            </>
          )}
        </main>
      </div>
      <div className="shrink-0">{commandBar}</div>
    </div>
  );
}
