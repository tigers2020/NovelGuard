# NovelGuard — Domain & Layer Context

> **Purpose:** Shared vocabulary for humans and agents. Runtime truth remains [`current_architecture.md`](current_architecture.md).

## Workflow (user-facing)

```text
scan → filename parse → blocking → relation detect → (exact/near) → group
     → dry-run preview → user approval → move/cleanup
```

Destructive file operations require **dry-run preview** and explicit user approval.

## Domain terms

| Term | Meaning | Primary code |
|------|---------|--------------|
| **FileEntry** | Immutable facts for one scanned file (path, size, mtime, extension, flags) | `domain/entities/file_entry.py` |
| **FilenameParseResult** | Parsed title, range segments, tags, confidence from filename | `domain/value_objects/filename_parse_result.py` |
| **BlockingGroup** | Candidate bucket of files for duplicate comparison (efficiency) | `domain/value_objects/blocking_group.py` |
| **DuplicateRelation** | Exact / near / containment / version edge between files | `domain/value_objects/duplicate_relation.py` |
| **DuplicateGroupResult** | Group verdict: member file ids, keeper, confidence, evidence | `application/dto/duplicate_group_result.py` |
| **Keeper** | File recommended to keep in a duplicate group | `domain/services/keeper_score_service.py` |
| **ScanRequest / ScanResult** | Scan input/output DTOs | `application/dto/scan_request.py`, `scan_result.py` |

## Layer map (where code lives)

| Layer | Path | Depends on |
|-------|------|------------|
| **domain** | `src/domain/` | `domain/*`, `domain/ports/*` only |
| **application** | `src/application/` | `domain`, `application/ports`, `application/constants`, `application/exceptions` |
| **infrastructure** | `src/infrastructure/` | `application` ports/DTOs, `domain` entities/VOs, `domain/ports` (adapters) |
| **gui** | `src/gui/` | `application` (use cases, DTOs, ports), `domain` entities/VOs where needed |
| **app** | `src/app/` | All layers — **composition root only** |

## Ports (application seams)

| Port | Role |
|------|------|
| `IJobRunner` | Start/cancel scan & duplicate jobs; progress via subscribe |
| `IIndexRepository` | Persist scan runs and file index |
| `FileScanner` | Walk filesystem for `FileEntry` list |
| `IFileDataStore` | In-memory scan/duplicate session state for UI |
| `ILogSink` | Structured log entries (`LogEntry` DTO) |

## Domain ports (outbound from domain)

| Port | Role |
|------|------|
| `IHashService` | SHA256 full/prefix/suffix hashes for exact duplicate detection |
| `ISimHashService` | SimHash similarity for near-duplicate (optional) |

Implementations: `infrastructure/hashing/hash_service_adapter.py`.

## Constants & settings (do not confuse)

| Module | Contents |
|--------|----------|
| `application/constants.py` | `Constants` class, `DEFAULT_TEXT_EXTENSIONS` — business policy |
| `app/settings/constants.py` | `SETTINGS_KEY_*` for QSettings only; re-exports `Constants` / extensions for GUI |

## Documentation map

| Document | Use when |
|----------|----------|
| [`docs/current_architecture.md`](current_architecture.md) | Layers, entry points, verification |
| [`docs/CONTEXT.md`](CONTEXT.md) | Terms and module map (this file) |
| [`docs/superpowers/specs/`](superpowers/specs/) | Approved **new** design specs |
| [`docs/superpowers/plans/`](superpowers/plans/) | Approved implementation plans |
| [`DESIGN.md`](../DESIGN.md) (repo root) | UI tokens for `@google/design.md` — not runtime architecture |
| [`documents/`](../documents/) | Historical memos — read-only |

## Recent architecture decisions (2026-05-22)

- Hash ports moved to `domain/ports/`; domain services no longer take `log_sink`.
- Duplicate pipeline assembled in `app/main.py` / `app/factories.py`, injected into `QtJobManager` → `DuplicateDetectionWorker`.
- Index DB errors surface as `application.exceptions.IndexPersistenceError` (not `sqlite3` in use cases).

Spec: [`superpowers/specs/2026-05-22-layer-seams-and-composition-design.md`](superpowers/specs/2026-05-22-layer-seams-and-composition-design.md).
