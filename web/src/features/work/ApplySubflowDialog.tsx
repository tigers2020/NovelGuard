import { useState } from "react";
import type { SelectionScope } from "../../types/selection";
import { useBridge } from "../../app/providers/SnapshotProvider";

type Step = "preview" | "confirm" | "apply";

export function ApplySubflowDialog({
  open,
  selection,
  onClose,
}: {
  open: boolean;
  selection: SelectionScope | null;
  onClose: () => void;
}) {
  const bridge = useBridge();
  const [step, setStep] = useState<Step>("preview");
  const [previewCount, setPreviewCount] = useState(0);
  const [busy, setBusy] = useState(false);

  if (!open || !selection) return null;

  const runPreview = async () => {
    setBusy(true);
    try {
      const result = await bridge.getMovePreview(selection);
      setPreviewCount(result.rows.length);
      setStep("confirm");
    } finally {
      setBusy(false);
    }
  };

  const runApply = async () => {
    setBusy(true);
    try {
      await bridge.applyResolvedActions(selection);
      onClose();
      setStep("preview");
      setPreviewCount(0);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-2xl rounded-md border border-outline bg-surface p-5">
        <h2 className="text-lg font-bold text-on-surface">이동 계획 적용</h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          dry-run → confirm → apply. Progress는 GlobalCommandBar만 표시합니다.
        </p>

        <ol className="mt-4 grid gap-2 md:grid-cols-3">
          {(
            [
              ["preview", "1. Preview", "이동·충돌·대상 폴더 검토"],
              ["confirm", "2. Confirm", "파괴적 작업 전 명시 확인"],
              ["apply", "3. Apply", "Python command로 적용"],
            ] as const
          ).map(([id, title, text]) => (
            <li
              key={id}
              className={`rounded-md border p-3 text-sm ${
                step === id ? "border-primary bg-primary/10" : "border-outline"
              }`}
            >
              <p className="font-semibold text-on-surface">{title}</p>
              <p className="mt-1 text-on-surface-variant">{text}</p>
            </li>
          ))}
        </ol>

        {step === "confirm" && (
          <p className="mt-4 text-sm text-on-surface">
            미리보기 대상: <strong>{previewCount}</strong> rows
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-outline px-3 py-2 text-sm font-semibold hover:bg-hover"
          >
            취소
          </button>
          {step === "preview" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void runPreview()}
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
            >
              미리보기
            </button>
          )}
          {step === "confirm" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void runApply()}
              className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
            >
              선택한 이동 적용
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
