# NovelGuard automation (in-repo)

Hermes / Telegram dispatcher writes jobs to the queue; **one worker** runs Cursor CLI on an isolated branch.

## Quick start (Linear automation)

```powershell
# Terminal 1 — tunnel (keep running)
ngrok http 8765

# Terminal 2 — webhook + worker (one process)
python scripts/automation_daemon.py
# or: .\automation\run-automation.ps1
```

Linear status change → webhook enqueue → worker runs job automatically.

Doctor: `python scripts/linear_webhook_doctor.py`

### Dashboard (default in PowerShell)

```powershell
# Use the same Python as run-automation.ps1 (.venv), not global pip:
.\.venv\Scripts\python.exe -m pip install -e ".[automation]"
.\automation\run-automation.ps1
```

Interactive TTY shows a Rich Live dashboard (queue, Linear events, agent output).

Flags on `scripts/automation_daemon.py`:
- `--plain` — line logs only (CI / pipes)
- `--tui` — force dashboard in non-TTY

## Manual / Hermes

```powershell
# Copy config; enable dry_run until Cursor CLI is on PATH
Copy-Item automation\config.example.yaml automation\config.yaml
pip install pyyaml   # or: pip install -e ".[automation]"

# Enqueue
python scripts/automation_enqueue.py --kind implement --task "Fix typo in README"

# Process one job (daemon must be stopped, or use --force)
python scripts/automation_worker.py --once
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
  prompts/             # templates (Linear: prompts/linear/{status}/)
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
