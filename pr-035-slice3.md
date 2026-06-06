## Summary

Implements 035 Slice 3: resolve auto-approve background job mutation execution.

This extends the Slice 2 dry-run job into a full background execution pipeline:

```text
summarize → set_keeper → approve → persist
```

## Scope

Included:

* `run_resolve_auto_approve_job()` full worker pipeline
* chunked mutation execution with `JOB_MUTATION_CHUNK = 200`
* reuse of `UpdateReviewDecisionsUseCase`
* keeper decision updates before approve decisions
* cooperative cancellation at page/chunk/phase boundaries
* persist phase projection rebuild
* snapshot mutation counters:
  * `keeperSetCount`
  * `approvedRowCount`
  * `mutationCount`
  * `persistedRevision`
* `library_revision` mutation behavior tests

Explicitly excluded:

* no Resolve UI wiring
* no buttons
* no progress bar UI
* no toast/dialog behavior
* no file move behavior
* no apply preview UI changes

## Contract Notes

The summary payload now includes `approveRowIds` for Slice 3 mutation execution.

This is an additive contract extension and is covered by Python bridge tests and web contract tests.

## Verification

```text
pytest tests/test_bridge_contract.py -k "resolve_auto_approve or summarize_resolve"
# 10 passed

cd web && npm run test:contracts
# 102 passed

cd web && npm run lint
# pass

ruff
# pass
```

## Safety

* Bridge `update_review_decisions()` behavior is preserved.
* Chunk execution skips cache rebuild during mutation and performs a full review index/projection rebuild in persist.
* Cancel before mutation preserves `library_revision`.
* Mutation execution changes `library_revision` only when review decisions are actually applied.
