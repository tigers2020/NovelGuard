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

describe("ResolveGridToolbar", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows move-ready and review-signal chips instead of Queue", () => {
    render(<ResolveGridToolbar {...baseProps} />);
    expect(screen.getByText("이동 대기")).toBeTruthy();
    expect(screen.getByText("참고 신호")).toBeTruthy();
    expect(screen.queryByText("Queue")).toBeNull();
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
