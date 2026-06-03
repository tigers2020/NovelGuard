# persona

Persona files are optional review lenses, not default workflow gates.

Use them only for non-trivial source/test work where a specific perspective helps.
Do not use persona roleplay for small fixes, docs-only work, read-only Q&A, or lint/format tasks.

Canonical policy: [AGENTS.md](../AGENTS.md).
Activation rule: [.cursor/rules/20-persona-dialogue.mdc](../.cursor/rules/20-persona-dialogue.mdc).

| Role | Card | Primary path |
| ---- | ---- | ------------ |
| Coordinator | [simon.md](simon.md) | Coordination, `app/` |
| Domain | [dominic.md](dominic.md) | `src/domain/` |
| Application | [yuri.md](yuri.md) | `src/application/` |
| Infrastructure | [ada.md](ada.md) | `src/infrastructure/` |
| GUI | [gina-gui.md](gina-gui.md) | `web/` |
| Tests | [tess.md](tess.md) | `tests/` |
| Verification | [rex.md](rex.md) | Verification |

When used, brief once before the first relevant code edit. Do not repeat persona assignment per file.
