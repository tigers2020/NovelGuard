import type {
  ResolveAutoApproveJobPhase,
  ResolveAutoApproveJobStatus,
} from "../../../types/resolveAutoApproveJob";

export function resolveAutoApproveStatusLabel(status: ResolveAutoApproveJobStatus): string {
  switch (status) {
    case "idle":
      return "자동 선정·승인 준비됨";
    case "running":
      return "자동 선정·승인 진행 중";
    case "complete":
      return "자동 선정·승인 완료";
    case "error":
      return "자동 선정·승인 실패";
    case "cancelled":
      return "자동 선정·승인 취소됨";
  }
}

export function resolveAutoApprovePhaseLabel(phase: ResolveAutoApproveJobPhase): string | null {
  if (phase === "idle") {
    return null;
  }
  return phase;
}
