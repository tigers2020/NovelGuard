import type { RowTypeFilter } from "./previewEligibility";

export const FORBIDDEN_PREVIEW_CTA_PHRASES = [
  "자동 정리 시작",
  "중복 파일 처리",
  "바로 이동",
] as const;

export function previewCtaLabel({
  filter,
  executableCount = 0,
  moveReadyCount,
}: {
  filter: RowTypeFilter;
  executableCount?: number;
  moveReadyCount?: number;
}): string {
  if (filter !== "exact") {
    return "이동 계획 미리보기";
  }

  const count = moveReadyCount ?? executableCount;
  if (count > 0) {
    return `Exact ${count}건 이동 계획 미리보기`;
  }
  return "Exact 중복 이동 계획 미리보기";
}
