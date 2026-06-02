import {
  OPTIONAL_QUALITY_COLUMN_KEYS,
  QUALITY_GRID_COLUMNS_KEY,
  QUALITY_GRID_SIZING_KEY,
  qualityGridDefaultVisibility,
} from "./qualityGridColumns";

export function loadQualityColumnVisibility(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(QUALITY_GRID_COLUMNS_KEY);
    if (!raw) return { ...qualityGridDefaultVisibility };
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return { ...qualityGridDefaultVisibility, ...parsed, name: true };
  } catch {
    return { ...qualityGridDefaultVisibility };
  }
}

export function saveQualityColumnVisibility(visibility: Record<string, boolean>): void {
  const payload: Record<string, boolean> = {};
  for (const key of OPTIONAL_QUALITY_COLUMN_KEYS) {
    if (visibility[key] !== undefined) {
      payload[key] = visibility[key] !== false;
    }
  }
  localStorage.setItem(QUALITY_GRID_COLUMNS_KEY, JSON.stringify(payload));
}

export function loadQualityColumnSizing(): Record<string, number> {
  try {
    const raw = localStorage.getItem(QUALITY_GRID_SIZING_KEY);
    return raw ? (JSON.parse(raw) as Record<string, number>) : {};
  } catch {
    return {};
  }
}
