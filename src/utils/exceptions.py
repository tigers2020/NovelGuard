"""
NovelGuard 커스텀 예외 모듈

프로젝트 전반에서 사용되는 커스텀 예외 클래스를 정의합니다.
"""


class NovelGuardError(Exception):
    """NovelGuard 기본 예외 클래스.
    
    모든 NovelGuard 관련 예외의 기본 클래스입니다.
    """
    pass


class FileScanError(NovelGuardError):
    """파일 스캔 관련 오류.
    
    파일 스캔 중 발생하는 오류를 나타냅니다.
    """
    pass


class FileEncodingError(NovelGuardError):
    """파일 인코딩 관련 오류.
    
    파일 인코딩 감지 또는 변환 중 발생하는 오류를 나타냅니다.
    """
    pass


class DuplicateAnalysisError(NovelGuardError):
    """중복 분석 오류.
    
    중복 파일 분석 중 발생하는 오류를 나타냅니다.
    """
    pass


class IntegrityCheckError(NovelGuardError):
    """무결성 검사 오류.
    
    파일 무결성 검사 중 발생하는 오류를 나타냅니다.
    """
    pass
