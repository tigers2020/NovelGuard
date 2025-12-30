# NovelGuard

> 텍스트 소설 파일 정리 도구 - 중복 제거, 신구 버전 분리, 무결성 검사

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
├── protocols/          # 프로토콜 문서
│   ├── README.md
│   └── development_protocol.md
├── persona/            # 페르소나 관련 파일
│   ├── README.md
│   └── novelguard_developer.md
├── src/                # 소스 코드
│   ├── __init__.py
│   └── main.py
├── tests/              # 테스트 코드
│   └── __init__.py
├── requirements.txt    # 의존성 패키지
├── agent.md           # Cursor AI용 타이딩 오케스트레이터
└── README.md          # 프로젝트 설명
```

## 설치 방법

### 필수 요구사항
- Python 3.10 이상
- Windows / macOS / Linux

### 설치

```bash
# 저장소 클론
git clone <repository-url>
cd NovelGuard

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 사용 방법

### 실행

```bash
python src/main.py
```

### 기본 워크플로우

1. **폴더 선택**: 정리할 소설 파일이 있는 폴더 선택
2. **스캔 시작**: 파일 스캔 및 분석 시작
3. **결과 확인**: 중복 파일, 무결성 문제 등 확인
4. **Dry-run**: 실제 변경 전 미리보기
5. **승인 및 적용**: 검토 후 승인하여 적용

## 개발 가이드

프로젝트의 `protocols/`와 `persona/` 폴더를 참고하여 개발을 진행합니다.

### 개발 문서

- **[개발 프로토콜](./protocols/development_protocol.md)**: 개발 절차, 코딩 컨벤션, 작업 흐름
- **[개발 페르소나](./persona/novelguard_developer.md)**: 개발 원칙, 역할 및 책임, 작업 스타일

### 개발 단계

- **MVP v1**: 기본 스캔, 중복 제거, 무결성 검사, GUI
- **v1.5**: 파일명 파싱, 신구 버전 판정, 백업/Undo
- **v2**: 유사본 탐지, 커스텀 규칙, 시리즈 그룹핑

자세한 내용은 [개발 프로토콜](./protocols/development_protocol.md)을 참고하세요.

## 라이브러리

### 필수
- **PySide6**: GUI 프레임워크
- **charset-normalizer**: 파일 인코딩 자동 감지
- **pydantic**: 데이터 모델 검증
- **PyInstaller**: 실행 파일 패키징

### 강력 추천
- **rich**: CLI 디버깅

자세한 내용은 `requirements.txt`를 참고하세요.

## 라이선스

(라이선스 정보를 여기에 추가하세요)

## 기여

(기여 가이드를 여기에 추가하세요)

