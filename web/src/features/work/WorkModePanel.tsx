import type { ReactNode } from "react";

export function WorkModePanel({ active, children }: { active: boolean; children: ReactNode }) {
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
