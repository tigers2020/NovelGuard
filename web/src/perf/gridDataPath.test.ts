import { describe, expect, it } from "vitest";
import { filterReviewRows, getAllReviewRows, paginateRows } from "../bridge/mockData";
import { filterPaginateLatencyBudgetMs } from "../components/grid/virtualWindow";

describe("grid data path", () => {
  it("filter+paginate 1284 rows under budget", () => {
    const all = getAllReviewRows(1284);
    const query = { viewMode: "all" as const, cursor: null, limit: 100 };
    const times: number[] = [];
    for (let i = 0; i < 20; i++) {
      const t0 = performance.now();
      const filtered = filterReviewRows(all, query);
      paginateRows(filtered, null, 100);
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    const median = times[Math.floor(times.length / 2)]!;
    expect(median).toBeLessThan(filterPaginateLatencyBudgetMs());
  });
});
