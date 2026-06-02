import type { FileRowColumnPreset, FileRowDensity } from "../../types/fileRows";

const PREFIX = "novelguard.shellFileDock.v1";

export type ShellFileDockPersisted = {
  expanded: boolean;
  heightPx: number;
  density: FileRowDensity;
  columnPreset: FileRowColumnPreset;
};

const DEFAULT_HEIGHT_PX = Math.round(
  typeof window !== "undefined" ? window.innerHeight * 0.28 : 240,
);

export const SHELL_FILE_DOCK_DEFAULTS: ShellFileDockPersisted = {
  expanded: false,
  heightPx: DEFAULT_HEIGHT_PX,
  density: "comfortable",
  columnPreset: "basic",
};

function read(key: string): string | null {
  try {
    return localStorage.getItem(`${PREFIX}.${key}`);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(`${PREFIX}.${key}`, value);
  } catch {
    /* ignore quota / private mode */
  }
}

function parseExpanded(raw: string | null): boolean {
  return raw === "true";
}

function parseHeightPx(raw: string | null): number {
  if (!raw) return SHELL_FILE_DOCK_DEFAULTS.heightPx;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return SHELL_FILE_DOCK_DEFAULTS.heightPx;
  return clampHeightPx(n);
}

function parseDensity(raw: string | null): FileRowDensity {
  return raw === "compact" ? "compact" : "comfortable";
}

function parsePreset(raw: string | null): FileRowColumnPreset {
  if (raw === "review") return "review";
  if (raw === "technical") return "technical";
  return "basic";
}

export function clampHeightPx(px: number): number {
  if (typeof window === "undefined") {
    return Math.min(Math.max(180, px), 480);
  }
  const max = Math.round(window.innerHeight * 0.45);
  return Math.min(Math.max(180, px), max);
}

export function loadShellFileDockState(): ShellFileDockPersisted {
  return {
    expanded: parseExpanded(read("expanded")),
    heightPx: parseHeightPx(read("heightPx")),
    density: parseDensity(read("density")),
    columnPreset: parsePreset(read("columnPreset")),
  };
}

export function persistShellFileDockState(state: ShellFileDockPersisted): void {
  write("expanded", state.expanded ? "true" : "false");
  write("heightPx", String(clampHeightPx(state.heightPx)));
  write("density", state.density);
  write("columnPreset", state.columnPreset);
}
