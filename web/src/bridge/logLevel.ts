import type { LogLevel } from "../types/logs";

const LEVEL_RANK: Record<LogLevel, number> = {
  DEBUG: 10,
  INFO: 20,
  WARNING: 30,
  ERROR: 40,
};

export function filterByMinLevel<T extends { level: LogLevel }>(
  entries: T[],
  minLevel: LogLevel | undefined,
): T[] {
  if (!minLevel) {
    return entries;
  }
  const threshold = LEVEL_RANK[minLevel];
  return entries.filter((entry) => LEVEL_RANK[entry.level] >= threshold);
}
