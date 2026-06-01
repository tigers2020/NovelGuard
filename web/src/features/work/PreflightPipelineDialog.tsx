import type { ResolveSnapshot } from "../../types/snapshot";

export function PreflightPipelineDialog({
  open,
  resolve,
  onClose,
  onGoResolve,
  onContinue,
}: {
  open: boolean;
  resolve: ResolveSnapshot;
  onClose: () => void;
  onGoResolve: () => void;
  onContinue: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-lg rounded-md border border-outline bg-surface p-5">
        <h2 className="text-lg font-bold text-on-surface">전체 실행 사전 확인</h2>
        <ul className="mt-4 space-y-2 text-sm text-on-surface-variant">
          <li>미검토/대기 큐: {resolve.queueCount}</li>
          <li>충돌: {resolve.conflictCount}</li>
          <li>미확인 적용 미리보기: {resolve.hasPendingApply ? "있음" : "없음"}</li>
        </ul>
        <p className="mt-3 text-sm text-on-surface-variant">
          검토 · 정리에서 해결한 뒤 전체 파이프라인을 실행하는 것을 권장합니다.
        </p>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
          >
            닫기
          </button>
          <button
            type="button"
            onClick={onGoResolve}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
          >
            검토 · 정리로 이동
          </button>
          <button
            type="button"
            onClick={onContinue}
            className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
          >
            그래도 계속
          </button>
        </div>
      </div>
    </div>
  );
}
