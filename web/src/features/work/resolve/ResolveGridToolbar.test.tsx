import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResolveGridToolbar } from "./ResolveGridToolbar";

const noop = vi.fn();

describe("ResolveGridToolbar", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows move-ready and review-signal chips without Queue label", () => {
    render(
      <ResolveGridToolbar
        moveReadyCount={3}
        reviewSignalCount={5}
        groupCount={2}
        conflictCount={1}
        approvedCount={4}
        rowTypeFilter="all"
        onRowTypeFilterChange={noop}
        search=""
        onSearchChange={noop}
        loading={false}
        queryError={null}
        onRetry={noop}
        onOpenFinalize={noop}
      />,
    );

    expect(screen.getByText("이동 대기")).toBeTruthy();
    expect(screen.getByText("참고 신호")).toBeTruthy();
    expect(screen.queryByText("Queue")).toBeNull();
    expect(screen.getByText("Groups")).toBeTruthy();
    expect(screen.getByText("Conflicts")).toBeTruthy();
    expect(screen.getByText("Approved")).toBeTruthy();
  });
});
