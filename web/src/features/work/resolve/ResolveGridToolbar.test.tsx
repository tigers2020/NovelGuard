import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResolveGridToolbar } from "./ResolveGridToolbar";

const noop = vi.fn();

function renderToolbar(
  overrides: Partial<Parameters<typeof ResolveGridToolbar>[0]> = {},
) {
  render(
    <ResolveGridToolbar
      queueCount={1}
      groupCount={2}
      conflictCount={0}
      approvedCount={3}
      rowTypeFilter="exact"
      onRowTypeFilterChange={noop}
      search=""
      onSearchChange={noop}
      loading={false}
      queryError={null}
      onRetry={noop}
      onOpenFinalize={noop}
      {...overrides}
    />,
  );
}

describe("ResolveGridToolbar primary preview CTA (NOV-30)", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows enabled primary CTA with label when exact filter and preview allowed", () => {
    renderToolbar({
      showPreviewCta: true,
      onPreview: noop,
      previewLabel: "Exact 2건 이동 계획 미리보기",
    });

    const cta = screen.getByTestId("resolve-preview-primary") as HTMLButtonElement;
    expect(cta.disabled).toBe(false);
    expect(cta.textContent).toBe("Exact 2건 이동 계획 미리보기");
  });

  it("hides primary CTA when showPreviewCta is false (review-only filters)", () => {
    renderToolbar({
      rowTypeFilter: "near",
      showPreviewCta: false,
      onPreview: noop,
      previewLabel: "이동 계획 미리보기",
    });

    expect(screen.queryByTestId("resolve-preview-primary")).toBeNull();
  });

  it("disables primary CTA with title when preview blocked on exact filter", () => {
    const reason = "현재 필터에 이동 미리보기 가능한 항목이 없습니다.";
    renderToolbar({
      showPreviewCta: true,
      onPreview: noop,
      previewDisabled: true,
      previewDisabledReason: reason,
      previewLabel: "Exact 중복 이동 계획 미리보기",
    });

    const cta = screen.getByTestId("resolve-preview-primary") as HTMLButtonElement;
    expect(cta.disabled).toBe(true);
    expect(cta.title).toBe(reason);
  });
});
