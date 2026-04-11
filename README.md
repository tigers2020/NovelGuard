# NovelGuard

> 텍스트 소설 파일 정리 도구 - 중복 제거, 신구 버전 분리, 무결성 검사

**현행 구조·진입점·검증의 문서 정본**: [docs/current_architecture.md](docs/current_architecture.md) · 지원 Python·의존성 하한: [`pyproject.toml`](pyproject.toml)

## 프로젝트 개요

NovelGuard는 다운로드받은 텍스트 소설 파일을 안전하게 정리하는 도구입니다.

### 주요 기능

- **중복 파일 탐지**: 단계적 중복 판정 (Raw Hash → Normalized Hash → Similarity)
- **신구 버전 분리**: 파일명 패턴, 수정일, 파일 크기 기반 판정
- **무결성 검사**: 인코딩 검증, 깨진 문자 탐지, 빈 파일 탐지
- **메타데이터 추출**: 제목, 작가, 회차 자동 파싱
- **안전한 처리**: Dry-run 모드, 원본 백업, Undo 기능

### 핵심 철학

- **안전성 우선**: 모든 변경은 사용자 승인 후 적용
- **보수적 접근**: 확실한 것만 처리, 애매한 경우는 사용자 확인
- **사용자 중심**: 명확한 피드백, 학습 가능, 커스터마이징 지원

## 프로젝트 구조

```
NovelGuard/
├── AGENTS.md           # Cursor·기여 게이트, 검증 명령, 규칙 우선순위
├── documents/          # 감사·플랜·조사 메모 (운영 게이트 문서)
├── docs/
│   ├── README.md                 # 문서 인덱스
│   ├── current_architecture.md   # 현행 구조 정본
│   ├── entry_points.md           # 실행 진입점 상세
│   └── archive/                  # 리팩터링·Phase 보고 등 역사 자료
├── protocols/          # 절차 요약 (정책 정본은 AGENTS.md + .cursor/rules/)
├── persona/            # 페르소나·역할 (톤·책임; 정책은 AGENTS.md 위임)
├── src/
│   ├── main.py         # 공식 진입점 (sys.path 설정 후 app.main)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── gui/
│   └── app/            # composition root: app/main.py
├── tests/              # pytest (기본 수집 경로는 pyproject.toml 참고)
├── pyproject.toml      # 프로젝트 메타·Python 버전·도구 설정 정본
├── requirements.txt    # 런타임 의존성 (pyproject와 동일 하한)
└── README.md
```

## 설치 방법

### 필수 요구사항

- **Python 3.12 이상** (`pyproject.toml`의 `requires-python`과 동일)
- Windows / macOS / Linux

### 설치

```bash
git clone <repository-url>
cd NovelGuard

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 런타임만
pip install -r requirements.txt
# 또는 (권장) 메타데이터 기준 설치
pip install -e .

# 개발·검증 (pytest, ruff, mypy, black, psutil)
pip install -e ".[dev]"
```

이전에 `requirements.txt` 한 줄로 테스트까지 설치하던 경우, 위처럼 **`pip install -e ".[dev]"`를 추가**하면 된다.

## 사용 방법

### 실행

프로젝트 루트에서:

```bash
python src/main.py
```

또는 `run.bat` / `run.ps1` (동일하게 `src/main.py` 호출).

보조: `cd src` 후 `python -m app.main` — [docs/entry_points.md](docs/entry_points.md) 참고.

### 기본 워크플로우

1. **폴더 선택**: 정리할 소설 파일이 있는 폴더 선택
2. **스캔 시작**: 파일 스캔 및 분석 시작
3. **결과 확인**: 중복 파일, 무결성 문제 등 확인
4. **Dry-run**: 실제 변경 전 미리보기
5. **승인 및 적용**: 검토 후 승인하여 적용

## 개발 가이드

- **[AGENTS.md](AGENTS.md)**: Persona Dialogue, 플랜 승인 게이트, MCP·검증 파이프라인
- **[docs/current_architecture.md](docs/current_architecture.md)**: 레이어·진입점·테스트 정책
- **[protocols/development_protocol.md](protocols/development_protocol.md)**: 절차·컨벤션
- **[persona/novelguard_developer.md](persona/novelguard_developer.md)**: 역할·안전 원칙

### 개발 단계 (로드맵)

- **MVP v1**: 기본 스캔, 중복 제거, 무결성 검사, GUI
- **v1.5**: 파일명 파싱, 신구 버전 판정, 백업/Undo
- **v2**: 유사본 탐지, 커스텀 규칙, 시리즈 그룹핑

## 런타임 라이브러리

`requirements.txt` / `pyproject.toml` `[project].dependencies`와 동일:

- **PySide6** — GUI
- **charset-normalizer** — 인코딩 감지
- **pydantic** — 데이터 검증
- **xxhash** — 빠른 해시

### 선택 (패키징·도구·문서 예시용)

- **PyInstaller** — 실행 파일 빌드 시 별도 설치
- **rich** — CLI/디버깅 편의용

## 라이선스

(라이선스 정보를 여기에 추가하세요)

## 기여

(기여 가이드를 여기에 추가하세요)
