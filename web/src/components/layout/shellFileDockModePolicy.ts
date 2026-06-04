import type { WorkMode } from "../../types/snapshot";
import {
  loadFileDockExpandedForMode,
  persistFileDockExpandedForMode,
} from "./shellFileDockStorage";

/** LOCK-LAYOUT-2: collapse dock when entering Resolve or Quality. */
export function shouldCollapseFileDockForWorkMode(mode: WorkMode): boolean {
  return mode === "resolve" || mode === "quality";
}

/** Scan may auto-expand via explicit CTA (scan-open-file-dock), not on every mode entry. */
export function shouldExpandFileDockForWorkMode(mode: WorkMode, fileCount: number): boolean {
  return mode === "scan" && fileCount > 0;
}

export function resolveInitialFileDockExpanded(activeMode: WorkMode): boolean {
  if (shouldCollapseFileDockForWorkMode(activeMode)) {
    return false;
  }
  return loadFileDockExpandedForMode(activeMode);
}

export function persistFileDockCollapseForWorkMode(mode: WorkMode): void {
  if (!shouldCollapseFileDockForWorkMode(mode)) {
    return;
  }
  persistFileDockExpandedForMode(mode, false);
}

export function fileDockExpandedForModeEntry(mode: WorkMode): boolean {
  if (shouldCollapseFileDockForWorkMode(mode)) {
    return false;
  }
  return loadFileDockExpandedForMode(mode);
}
