"""커스텀 예외 정의."""


class NovelGuardError(Exception):
    """NovelGuard 기본 예외."""
    pass


class FileEncodingError(NovelGuardError):
    """파일 인코딩 관련 오류."""
    pass


class DuplicateAnalysisError(NovelGuardError):
    """중복 분석 오류."""
    pass


class IntegrityCheckError(NovelGuardError):
    """무결성 검사 오류."""
    pass


class RepositoryError(NovelGuardError):
    """Repository 관련 오류."""
    pass

