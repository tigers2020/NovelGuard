import { bench, describe } from "vitest";
import { filterReviewRows, getAllReviewRows, paginateRows } from "../bridge/mockData";

const all = getAllReviewRows(1284);
const query = { viewMode: "all" as const, cursor: null, limit: 100 };

describe("grid data path bench", () => {
  bench("filter+paginate page", () => {
    const filtered = filterReviewRows(all, query);
    paginateRows(filtered, null, 100);
  });
});
