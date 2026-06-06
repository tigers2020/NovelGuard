# Git safety (agents + automation)

Prompt rules alone are insufficient. Automation enforces branch policy at **command** and **job** boundaries.

## Agent policy

Agents must work only on the **current** branch.

| Allowed (typical) | Forbidden |
|-----------------|-----------|
| `git status`, `git diff`, `git log` | `git checkout -b`, `git switch -c` |
| `git add`, `git commit` (when job allows) | `git checkout <branch>`, `git switch <branch>` |
| `git rev-parse`, `git branch --show-current` | `git branch <name>`, `git branch -D` |
| | `git merge`, `git rebase`, `git reset --hard` |
| | `git worktree add` |

If a branch operation seems necessary: **stop** and report the exact command. Do not run it.

## Command guard

`scripts/git_guard.py` wraps `git` for Cursor/Codex subprocesses.

- Wrappers: `.automation/bin/git` (POSIX), `.automation/bin/git.cmd` (Windows)
- Runner prepends `.automation/bin` to `PATH` before launching the agent
- Runner's own `_git()` calls use the real git binary (orchestrator branch prep only)

Human escape hatch (not set in automation):

```bash
NOVELGUARD_ALLOW_GIT_BRANCH_OPS=1 git checkout -b human-only
```

## Job preflight / postflight

At cursor start: `git rev-parse --abbrev-ref HEAD` → `start_branch` in job result.

After cursor: same check → `end_branch`. If different, job **fails** (`branch_guard_failed`).

## Orchestrator vs agent

| Role | Branch create/switch |
|------|----------------------|
| Human / orchestrator | Creates `ai/<issue>-…` (or configured prefix) via `prepare_branch` |
| Agent | Current branch only; guard blocks mutations |

## Other defenses

- Dirty-tree preflight before `prepare_branch` (refuses checkout over WIP)
- No `merge_approved` in job payloads
- Branch protection on `main` (remote)

See also: `.cursor/rules/05-git-safety.mdc`, [runner-brief.md](runner-brief.md).
