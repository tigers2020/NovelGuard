const KEY = "novelguard.resolveFacet.v1.expanded";

function read(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function write(value: string): void {
  try {
    localStorage.setItem(KEY, value);
  } catch {
    /* ignore quota / private mode */
  }
}

export function loadResolveFacetExpanded(): boolean {
  return read() === "true";
}

export function persistResolveFacetExpanded(expanded: boolean): void {
  write(expanded ? "true" : "false");
}
