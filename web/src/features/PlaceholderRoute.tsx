import { AppInfoDiagnostics } from "./AppInfoDiagnostics";

export function PlaceholderRoute({ title }: { title: string }) {
  return (
    <div className="h-full overflow-y-auto bg-background p-6">
      <div className="rounded-md border border-outline bg-surface p-6">
        <h1 className="text-xl font-bold text-on-surface">{title}</h1>
        <p className="mt-2 text-sm text-on-surface-variant">
          v1 shell parity. Review workspace ships in later PRs.
        </p>
        {title === "Settings" ? <AppInfoDiagnostics /> : null}
      </div>
    </div>
  );
}
