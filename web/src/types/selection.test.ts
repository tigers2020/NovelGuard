import { describe, expect, it } from "vitest";
import {
  EmptySelectionError,
  InvalidSelectionScopeError,
  validateSelectionScope,
} from "./selection";
import { currentQuerySelection, explicitRowsSelection } from "../contracts/fixtures";

describe("validateSelectionScope", () => {
  it("accepts explicit_rows with ids", () => {
    expect(() => validateSelectionScope(explicitRowsSelection)).not.toThrow();
  });

  it("rejects empty explicit_rows", () => {
    expect(() =>
      validateSelectionScope({ type: "explicit_rows", rowIds: [] }),
    ).toThrow(EmptySelectionError);
  });

  it("rejects current_query without viewMode", () => {
    expect(() =>
      validateSelectionScope({
        type: "current_query",
        query: {} as { viewMode: "action" },
        excludeRowIds: [],
      }),
    ).toThrow(InvalidSelectionScopeError);
  });

  it("rejects empty current_query when resolver returns 0", () => {
    expect(() =>
      validateSelectionScope(currentQuerySelection, () => 0),
    ).toThrow(EmptySelectionError);
  });

  it("accepts current_query when resolver returns > 0", () => {
    expect(() =>
      validateSelectionScope(currentQuerySelection, () => 5),
    ).not.toThrow();
  });

  it("supports excludeRowIds on current_query", () => {
    const scope = {
      type: "current_query" as const,
      query: { viewMode: "action" as const },
      excludeRowIds: ["r99"],
    };
    expect(() =>
      validateSelectionScope(scope, (_q, exclude) => {
        expect(exclude).toEqual(["r99"]);
        return 1;
      }),
    ).not.toThrow();
  });
});
