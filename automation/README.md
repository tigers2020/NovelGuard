# NovelGuard automation (in-repo)

Hermes / Telegram dispatcher writes jobs to the queue; **one worker** runs Cursor CLI on an isolated branch.

## Quick start

```powershell
# 1) Copy config; enable dry_run until Cursor CLI is on PATH
Copy-Item automation\config.example.yaml automation\config.yaml
pip install pyyaml   # or: pip install -e ".[automation]"

# 2) Enqueue
python scripts/automation_enqueue.py --kind implement --task "Fix typo in README"

# 3) Process one job
python scripts/automation_worker.py --once
# or: .\automation\run-worker.ps1

# 4) Loop (Task Scheduler / systemd)
python scripts/automation_worker.py
```

Hermes:

```powershell
python scripts/hermes_enqueue.py automation/examples/hermes-job.json --id job-1
Get-Content job.json -Raw | python scripts/hermes_job_stdin.py
python scripts/automation_worker.py --once
# loop: .\automation\run-worker-loop.ps1
```

Quick beta (no full pytest):

```powershell
python scripts/beta_gate.py
```

Worker refuses dirty working tree — commit/stash WIP on feature branch first.

## Layout

```text
automation/
  config.example.yaml
  config.yaml          # local, gitignored
  prompts/             # templates
  schemas/job-payload.schema.json
  jobs/queue.sqlite    # gitignored
  logs/                # gitignored
  locks/               # per-repo lock files
  runners/
    queue.py
    cursor_runner.py
    job_worker.py
    enqueue_job.py
```

Policy: [AGENTS.md](../AGENTS.md), [docs/agent-automation.md](../docs/agent-automation.md).

All Cursor CLI prompts are prefixed with `/caveman` (`cursor.prompt_prefix` in `config.yaml`; shared helper: `scripts/cursor_cli_common.py`).
