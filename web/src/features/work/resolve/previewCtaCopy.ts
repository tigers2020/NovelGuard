import type { RowTypeFilter } from "./previewEligibility";

export const FORBIDDEN_PREVIEW_CTA_PHRASES = [
  "자동 정리 시작",
  "중복 파일 처리",
  "바로 이동",
] as const;

export type PreviewCtaLabelInput = {
  filter: RowTypeFilter;
  executableCount?: number;
  moveReadyCount?: number;
};

export function previewCtaLabel({
  filter,
  executableCount = 0,
  moveReadyCount,
}: PreviewCtaLabelInput): string {
  const n = moveReadyCount ?? executableCount;
  if (filter === "exact" && n > 0) {
    return `Exact ${n}건 이동 계획 미리보기`;
  }
  if (filter === "exact") {
    return "Exact 중복 이동 계획 미리보기";
  }
  return "이동 계획 미리보기";
}
