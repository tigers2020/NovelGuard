import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResolveGridToolbar } from "./ResolveGridToolbar";

const baseProps = {
  moveReadyCount: 3,
  reviewSignalCount: 2,
  groupCount: 1,
  conflictCount: 0,
  approvedCount: 4,
  rowTypeFilter: "exact" as const,
  onRowTypeFilterChange: vi.fn(),
  search: "",
  onSearchChange: vi.fn(),
  loading: false,
  queryError: null,
  onRetry: vi.fn(),
  onOpenFinalize: vi.fn(),
};

const noop = vi.fn();

function renderToolbar(
  overrides: Partial<Parameters<typeof ResolveGridToolbar>[0]> = {},
) {
  render(<ResolveGridToolbar {...baseProps} {...overrides} />);
}

describe("ResolveGridToolbar", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows move-ready and review-signal chips without Queue label", () => {
    render(
      <ResolveGridToolbar
        {...baseProps}
        rowTypeFilter="all"
        reviewSignalCount={5}
        groupCount={2}
        conflictCount={1}
      />,
    );

    expect(screen.getByText("이동 대기")).toBeTruthy();
    expect(screen.getByText("참고 신호")).toBeTruthy();
    expect(screen.queryByText("Queue")).toBeNull();
    expect(screen.getByText("Groups")).toBeTruthy();
    expect(screen.getByText("Conflicts")).toBeTruthy();
    expect(screen.getByText("Approved")).toBeTruthy();
  });

  it("renders primary preview CTA when enabled", () => {
    render(
      <ResolveGridToolbar
        {...baseProps}
        showPreviewCta
        onPreview={vi.fn()}
        previewLabel="Exact 3건 이동 계획 미리보기"
      />,
    );
    expect(screen.getByTestId("resolve-preview-primary").textContent).toContain(
      "Exact 3건",
    );
  });
});

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

describe("ResolveGridToolbar type filter labels (NOV-29)", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows KO tab hints for exact, near, and relation filters", () => {
    renderToolbar();

    expect(screen.getByTestId("resolve-type-filter-exact").textContent).toBe("Exact (이동)");
    expect(screen.getByTestId("resolve-type-filter-near").textContent).toBe("Near (참고)");
    expect(screen.getByTestId("resolve-type-filter-relation").textContent).toBe("Relation (참고)");
    expect(screen.getByTestId("resolve-type-filter-all").textContent).toBe("All types");
  });
});
