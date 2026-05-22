## 2026-04-13 cleanup note

- Root-level legacy plans/reports and old `documents/` audit outputs were bundled into a local zip
  archive and removed from the working tree.
- The maintained source-of-truth set is now the repo root guides plus the curated `docs/` and
  `docs/archive/` trees.

# docs/

## 현행 정본 (이것만 우선하면 됨)

| 문서 | 내용 |
|------|------|
| [current_architecture.md](current_architecture.md) | 레이어, 진입점, 테스트·검증 정책 |
| [entry_points.md](entry_points.md) | `python src/main.py` 등 실행 방법 상세 |
| [superpowers/README.md](superpowers/README.md) | Superpowers 설계·구현 계획 (신규 spec/plan) |

버전·의존성·도구 설정은 저장소 루트의 [`pyproject.toml`](../pyproject.toml)가 단일 정본이다.

## 역사·계획 자료

리팩터링 Phase 보고, v1.4 분할 계획서, 구 성능 벤치 메모 등은 **[archive/](archive/README.md)** 아래에 모아 두었다. 코드나 경로와 불일치할 수 있으니, 동작 설명은 위 정본만 따른다.
