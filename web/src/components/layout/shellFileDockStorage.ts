import type { FileRowColumnPreset, FileRowDensity } from "../../types/fileRows";
import type { WorkMode } from "../../types/snapshot";

const PREFIX = "novelguard.shellFileDock.v1";

export type FileDockExpandMode = "scan" | "resolve" | "quality";

export type ShellFileDockPersisted = {
  expanded: boolean;
  heightPx: number;
  density: FileRowDensity;
  columnPreset: FileRowColumnPreset;
};

export type ShellFileDockLayout = Pick<
  ShellFileDockPersisted,
  "heightPx" | "density" | "columnPreset"
>;

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

function normalizeExpandMode(mode: WorkMode): FileDockExpandMode {
  if (mode === "resolve" || mode === "quality") {
    return mode;
  }
  return "scan";
}

function expandedKeyForMode(mode: WorkMode): string {
  return `expanded.${normalizeExpandMode(mode)}`;
}

export function clampHeightPx(px: number): number {
  if (typeof window === "undefined") {
    return Math.min(Math.max(180, px), 480);
  }
  const max = Math.round(window.innerHeight * 0.45);
  return Math.min(Math.max(180, px), max);
}

export function loadShellFileDockLayout(): ShellFileDockLayout {
  return {
    heightPx: parseHeightPx(read("heightPx")),
    density: parseDensity(read("density")),
    columnPreset: parsePreset(read("columnPreset")),
  };
}

export function persistShellFileDockLayout(layout: ShellFileDockLayout): void {
  write("heightPx", String(clampHeightPx(layout.heightPx)));
  write("density", layout.density);
  write("columnPreset", layout.columnPreset);
}

/** @deprecated Use loadFileDockExpandedForMode — expanded field reflects scan slot only. */
export function loadShellFileDockState(): ShellFileDockPersisted {
  return {
    expanded: loadFileDockExpandedForMode("scan"),
    ...loadShellFileDockLayout(),
  };
}

export function loadFileDockExpandedForMode(mode: WorkMode): boolean {
  const perMode = read(expandedKeyForMode(mode));
  if (perMode !== null) {
    return parseExpanded(perMode);
  }
  if (normalizeExpandMode(mode) === "scan") {
    const legacy = read("expanded");
    if (legacy !== null) {
      return parseExpanded(legacy);
    }
  }
  return SHELL_FILE_DOCK_DEFAULTS.expanded;
}

export function persistFileDockExpandedForMode(mode: WorkMode, expanded: boolean): void {
  write(expandedKeyForMode(mode), expanded ? "true" : "false");
}

export function persistShellFileDockState(state: ShellFileDockPersisted, activeMode?: WorkMode): void {
  persistShellFileDockLayout(state);
  const mode = activeMode ?? "scan";
  persistFileDockExpandedForMode(mode, state.expanded);
}
