# Cursor Memo

에이전트 세션에서 발견한 재현 가능한 실수·교훈·주의사항을 기록한다.

---

## 기록

| 날짜 | 내용 | 관련 파일 |
|------|------|-----------|
| 2026-04-11 | application → gui 순환 의존: `FileDataStore`를 `IFileDataStore` 포트로 분리 | `application/ports/file_data_store.py`, `application/dto/file_data.py` |
| 2026-04-11 | AGENTS/persona 문서의 `{{...}}` 플레이스홀더가 미치환 상태였음 — 실제 경로·프로젝트명으로 일괄 치환 | `AGENTS.md`, `.cursor/rules/*.mdc`, `persona/*.md` |
| 2026-04-11 | `testpaths`에 `tests/unit`이 있으나 Git 미추적이면 클론 후 `pytest` 건수가 문서(144 등)와 불일치 | `tests/unit/`, `tests/README.md`, `pyproject.toml` |
