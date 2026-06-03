import type { ReactNode } from "react";

export function WorkModePanel({
  active,
  children,
  layout = "overlay",
}: {
  active: boolean;
  children: ReactNode;
  /** stacked = in-flow height (Scan compact chrome); overlay = absolute stack for mode tabs */
  layout?: "overlay" | "stacked";
}) {
  if (layout === "stacked") {
    return (
      <section
        aria-hidden={!active}
        {...(!active ? { inert: true } : {})}
        className={active ? "flex flex-col shrink-0 overflow-hidden" : "hidden"}
      >
        {children}
      </section>
    );
  }

  return (
    <section
      aria-hidden={!active}
      {...(!active ? { inert: true } : {})}
      className={
        active
          ? "pointer-events-auto visible absolute inset-0 flex h-full min-h-0 flex-col overflow-hidden"
          : "pointer-events-none invisible absolute inset-0 flex h-full min-h-0 flex-col overflow-hidden"
      }
    >
      {children}
    </section>
  );
}
