/** User-visible Korean fallbacks when bridge errors lack a message. */
export const UI_FALLBACK = {
  loadFiles: "파일을 불러오지 못했습니다",
  loadLogs: "로그를 불러오지 못했습니다",
  loadSettings: "설정을 불러오지 못했습니다",
  saveSetting: "설정을 저장하지 못했습니다",
  loadAppInfo: "앱 정보를 불러오지 못했습니다",
} as const;

export function collapsedFileDockSrSummary(totalBytesLabel: string, issueCount: number): string {
  return `전체 크기 ${totalBytesLabel}, 이슈 ${issueCount}건`;
}

/** Prior English fallbacks that must not return in Korean UI surfaces. */
export const FORBIDDEN_ENGLISH_UI_FALLBACKS = [
  "Failed to load files",
  "Failed to load logs",
  "Failed to load settings",
  "Failed to save setting",
  "getAppInfo failed",
  "Total size",
] as const;
