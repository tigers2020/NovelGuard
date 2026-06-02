import type { VisibilityState } from "@tanstack/react-table";

const RESPONSIVE_THRESHOLDS: Record<string, number> = {
  severity: 280,
  encoding: 360,
  integrity: 440,
  issueType: 520,
  path: 600,
};

const LAYOUT_NOT_READY_WIDTH = 200;

export function mergeQualityColumnVisibility(containerWidth: number): VisibilityState {
  const merged: VisibilityState = { name: true };
  for (const [key, minWidth] of Object.entries(RESPONSIVE_THRESHOLDS)) {
    merged[key] = containerWidth >= LAYOUT_NOT_READY_WIDTH && containerWidth >= minWidth;
  }
  return merged;
}
