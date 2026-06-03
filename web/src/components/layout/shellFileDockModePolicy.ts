import type { WorkMode } from "../../types/snapshot";
import {
  loadShellFileDockState,
  persistShellFileDockState,
} from "./shellFileDockStorage";

/** LOCK-LAYOUT-2: collapse dock when entering Resolve or Quality. */
export function shouldCollapseFileDockForWorkMode(mode: WorkMode): boolean {
  return mode === "resolve" || mode === "quality";
}

/** Scan primary surface is FileDock — expand when library has indexed files. */
export function shouldExpandFileDockForWorkMode(mode: WorkMode, fileCount: number): boolean {
  return mode === "scan" && fileCount > 0;
}

export function resolveInitialFileDockExpanded(activeMode: WorkMode, fileCount = 0): boolean {
  const state = loadShellFileDockState();
  if (shouldCollapseFileDockForWorkMode(activeMode)) {
    if (state.expanded) {
      persistShellFileDockState({ ...state, expanded: false });
    }
    return false;
  }
  if (shouldExpandFileDockForWorkMode(activeMode, fileCount)) {
    persistShellFileDockState({ ...state, expanded: true });
    return true;
  }
  return state.expanded;
}

export function persistFileDockCollapseForWorkMode(mode: WorkMode): void {
  if (!shouldCollapseFileDockForWorkMode(mode)) {
    return;
  }
  const state = loadShellFileDockState();
  if (state.expanded) {
    persistShellFileDockState({ ...state, expanded: false });
  }
}

export function persistFileDockExpandForWorkMode(mode: WorkMode, fileCount: number): void {
  if (!shouldExpandFileDockForWorkMode(mode, fileCount)) {
    return;
  }
  persistShellFileDockState({ ...loadShellFileDockState(), expanded: true });
}
