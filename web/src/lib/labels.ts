import type { ProposedAction, ReviewRowType, ReviewStatus } from "../types/review";

export const reviewStatusLabel: Record<ReviewStatus, string> = {
  unreviewed: "미검토",
  approved: "승인",
  conflict: "충돌",
  excluded: "제외",
};

export const reviewTypeLabel: Record<ReviewRowType, string> = {
  exact: "Exact",
  near: "Near",
  relation: "Relation",
  move_only: "이동만",
};

export const proposedActionLabel: Record<ProposedAction, string> = {
  keep: "유지",
  move_duplicate: "중복 이동",
  move_organized: "정리 이동",
  ignore: "무시",
};
