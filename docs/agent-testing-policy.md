# Agent testing policy (NovelGuard)

Full test-creation and coverage rules. **Always-on summary:** `.cursor/rules/30-verify-gates.mdc`. **Canonical router:** [AGENTS.md](../AGENTS.md).

---

## Principles

- No indiscriminate test files — extend existing `tests/` modules first.
- **Meaningful coverage only** — behavior, regressions, spec acceptance criteria.
- Reproduced production bugs → regression test (with approval) + `documents/CURSOR_MEMO.md` when appropriate.

---

## New test files require explicit approval

User must say one of: `TEST_ALLOWED`, `create tests`, `add regression test`, `write a test for this bug`, or equivalent.

**Without approval you may:** inspect/run existing tests, explain what test would be needed, modify production code, update documentation.

**Forbidden without approval:**

- new `test_*.py`, `*_test.py`, `*.spec.*`, `*.test.*`
- new `tests/` subdirectories
- mock-only tests with no contract value
- relaxed assertions, golden churn, skip/xfail/delete to force pass
- tests for implementation details instead of contract behavior
- more than one new test file per task

---

## Before creating any new test file

1. Search for existing relevant tests.
2. Prefer editing the smallest existing test.
3. No duplicate coverage.
4. No broad snapshot/golden tests unless explicitly requested.

---

## If a test seems necessary but is not authorized

Stop and report:

```text
Test creation required but not authorized.

Reason:
- ...

Proposed minimal test:
- file:
- behavior:
- why existing tests are insufficient:
```

Then wait for explicit approval.

---

## Allowed exception (`TEST_ALLOWED`)

Minimum necessary:

- 1 new test file
- 1 focused regression case
- no golden/snapshot update unless separately approved

---

## Git guard

`scripts/guard_new_tests.py` (pre-commit) blocks staged new test files unless `ALLOW_NEW_TESTS=1` (Unix) or `$env:ALLOW_NEW_TESTS="1"` (PowerShell).
