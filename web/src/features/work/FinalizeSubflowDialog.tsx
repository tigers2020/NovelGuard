import { FinalizeSubflowContent } from "./FinalizeWorkspace";

export function FinalizeSubflowDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      data-testid="finalize-subflow-dialog"
    >
      <div
        className="relative z-[101] flex max-h-[92vh] w-full max-w-4xl flex-col rounded-md border border-outline bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-on-surface">최종 검증</h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              summary → blockers/warnings → cleanup opt-in → run → report. Progress는 GlobalCommandBar만 표시합니다.
            </p>
          </div>
          <button
            type="button"
            data-testid="finalize-subflow-close"
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
            onClick={onClose}
          >
            닫기
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto pr-1">
          <FinalizeSubflowContent compact />
        </div>
      </div>
    </div>
  );
}
