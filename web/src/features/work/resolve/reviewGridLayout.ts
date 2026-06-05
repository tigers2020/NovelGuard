import type { VisibilityState } from "@tanstack/react-table";

/** Progressive hide order when the grid scrollport is narrow (px cutoffs). `name` is always shown. */
const RESPONSIVE_THRESHOLDS: Record<string, number> = {
  status: 200,
  type: 260,
  proposedAction: 320,
  targetFolder: 380,
  confidence: 440,
  encoding: 520,
  integrity: 600,
  path: 680,
  sizeBytes: 760,
};

const LAYOUT_NOT_READY_WIDTH = 200;

/** Width-only column visibility for the resolve review grid. */
export function mergeReviewColumnVisibility(containerWidth: number): VisibilityState {
  const merged: VisibilityState = { name: true };
  for (const key of Object.keys(RESPONSIVE_THRESHOLDS)) {
    merged[key] =
      containerWidth >= LAYOUT_NOT_READY_WIDTH &&
      containerWidth >= RESPONSIVE_THRESHOLDS[key]!;
  }
  return merged;
}
