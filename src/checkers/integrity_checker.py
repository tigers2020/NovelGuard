"""
파일 무결성 검사 모듈

파일의 무결성을 검사하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Literal, Callable
import logging

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import IntegrityCheckError
from utils.constants import (
    INTEGRITY_DECODE_SAMPLE_SIZE,
    INTEGRITY_ISSUE_CODE_EMPTY_FILE,
    INTEGRITY_ISSUE_CODE_READ_ERROR,
    INTEGRITY_ISSUE_CODE_DECODE_ERROR,
    ENCODING_EMPTY,
    ENCODING_NOT_DETECTED,
    ENCODING_UNKNOWN,
    ENCODING_NA,
    DEFAULT_ENCODING,
    PROGRESS_UPDATE_INTERVAL,
)


class IntegrityIssue:
    """무결성 문제 정보를 나타내는 클래스.
    
    Attributes:
        path: 문제가 있는 파일의 경로
        code: 문제 코드 (예: "EMPTY_FILE", "DECODE_ERROR", "READ_ERROR")
        severity: 심각도 ("INFO", "WARN", "ERROR")
        message: 문제 설명 메시지 (사용자 표시용 한국어)
        meta: 추가 메타데이터 (인코딩 정보, 에러 상세 등)
    """
    
    def __init__(
        self,
        path: Path,
        code: str,
        severity: Literal["INFO", "WARN", "ERROR"],
        message: str,
        meta: Optional[dict] = None
    ) -> None:
        """IntegrityIssue 초기화.
        
        Args:
            path: 문제가 있는 파일의 경로
            code: 문제 코드
            severity: 심각도 ("INFO", "WARN", "ERROR")
            message: 문제 설명 메시지 (사용자 표시용 한국어)
            meta: 추가 메타데이터 (선택사항)
        """
        self.path = path
        self.code = code
        self.severity = severity
        self.message = message
        self.meta = meta or {}


class IntegrityChecker:
    """파일 무결성 검사 클래스.
    
    파일의 무결성을 검사하여 문제를 찾습니다.
    MVP v1에서는 인코딩 검증과 0바이트 파일 탐지만 수행합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _progress_callback: 진행 상황 업데이트 콜백 함수 (선택적)
    """
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """IntegrityChecker 초기화.
        
        Args:
            progress_callback: 진행 상황 업데이트 콜백 함수 (message: str) -> None
        """
        self._logger = get_logger("IntegrityChecker")
        self._progress_callback = progress_callback
    
    def _update_progress(self, message: str) -> None:
        """진행 상황을 업데이트합니다.
        
        Args:
            message: 진행 상황 메시지
        """
        if self._progress_callback:
            self._progress_callback(message)
        self._logger.debug(message)
    
    def check(self, file_records: list[FileRecord]) -> list[IntegrityIssue]:
        """파일 무결성을 검사하여 문제 리스트를 반환.
        
        각 파일에 대해 다음 검사를 순차적으로 수행합니다:
        1. 0바이트 파일 탐지
        2. 파일 접근성 검사 (존재/권한)
        3. 디코딩 검증 (감지된 인코딩으로 실제 디코딩 가능 여부)
        
        Args:
            file_records: 검사할 FileRecord 리스트
        
        Returns:
            발견된 무결성 문제 리스트 (IntegrityIssue 객체들)
        
        Raises:
            IntegrityCheckError: 검사 중 오류 발생 시
        """
        try:
            self._logger.info(f"무결성 검사 시작: {len(file_records)}개 파일")
            self._update_progress(f"무결성 검사 시작: {len(file_records)}개 파일")
            
            issues: list[IntegrityIssue] = []
            total_files = len(file_records)
            processed_count = 0
            
            for file_record in file_records:
                try:
                    # 1. 0바이트 파일 검사
                    empty_issue = self._check_empty_file(file_record)
                    if empty_issue:
                        issues.append(empty_issue)
                        # 0바이트 파일은 다른 검사 스킵
                        continue
                    
                    # 2. 파일 접근성 검사
                    read_issue = self._check_readable(file_record)
                    if read_issue:
                        issues.append(read_issue)
                        # 읽을 수 없으면 디코딩 검사 스킵
                        continue
                    
                    # 3. 디코딩 검증
                    decode_issue = self._check_decode_sample(file_record)
                    if decode_issue:
                        issues.append(decode_issue)
                        
                except Exception as e:
                    # 개별 파일 검사 실패 시 로그만 기록하고 계속 진행
                    self._logger.warning(
                        f"파일 무결성 검사 중 오류: {file_record.path} - {e}",
                        exc_info=True
                    )
                    # 예상치 못한 오류도 이슈로 기록
                    issues.append(IntegrityIssue(
                        path=file_record.path,
                        code=INTEGRITY_ISSUE_CODE_READ_ERROR,
                        severity="ERROR",
                        message=f"검사 중 오류 발생: {str(e)}",
                        meta={"error": str(e)}
                    ))
                
                # 진행 상황 업데이트 (PROGRESS_UPDATE_INTERVAL개마다 또는 마지막)
                processed_count += 1
                if (
                    processed_count % PROGRESS_UPDATE_INTERVAL == 0
                    or processed_count == total_files
                ):
                    self._update_progress(
                        f"무결성 검사 중: {processed_count}/{total_files} "
                        f"({len(issues)}개 문제 발견)"
                    )
            
            self._logger.info(f"무결성 검사 완료: {len(issues)}개 문제 발견")
            self._update_progress(f"무결성 검사 완료: {len(issues)}개 문제 발견")
            return issues
            
        except Exception as e:
            self._logger.error(f"무결성 검사 오류: {e}", exc_info=True)
            raise IntegrityCheckError(f"무결성 검사 중 오류 발생: {str(e)}") from e
    
    def _check_empty_file(self, file_record: FileRecord) -> Optional[IntegrityIssue]:
        """0바이트 파일을 검사합니다.
        
        파일이 존재하고 크기가 0인 경우에만 빈 파일로 판정합니다.
        존재하지 않는 파일은 이 검사에서 제외됩니다.
        
        Args:
            file_record: 검사할 FileRecord
        
        Returns:
            0바이트 파일인 경우 IntegrityIssue, 아니면 None
        """
        # 파일이 존재하고 크기가 0인 경우만 빈 파일로 판정
        if file_record.size == 0 and file_record.path.exists():
            return IntegrityIssue(
                path=file_record.path,
                code=INTEGRITY_ISSUE_CODE_EMPTY_FILE,
                severity="WARN",
                message="빈 파일 (0바이트)",
                meta={"size": 0}
            )
        return None
    
    def _check_readable(self, file_record: FileRecord) -> Optional[IntegrityIssue]:
        """파일 접근성(읽기 가능 여부)을 검사합니다.
        
        Args:
            file_record: 검사할 FileRecord
        
        Returns:
            읽을 수 없는 경우 IntegrityIssue, 아니면 None
        """
        try:
            # 파일 존재 여부 확인
            if not file_record.path.exists():
                return IntegrityIssue(
                    path=file_record.path,
                    code=INTEGRITY_ISSUE_CODE_READ_ERROR,
                    severity="ERROR",
                    message="파일이 존재하지 않음",
                    meta={"error": "FileNotFoundError"}
                )
            
            # 읽기 권한 확인 (stat으로 빠르게 확인)
            try:
                file_record.path.stat()
            except PermissionError as e:
                return IntegrityIssue(
                    path=file_record.path,
                    code=INTEGRITY_ISSUE_CODE_READ_ERROR,
                    severity="ERROR",
                    message="파일 읽기 권한 없음",
                    meta={"error": str(e)}
                )
            
            # 실제로 파일을 열 수 있는지 확인 (바이너리 모드로 빠르게)
            try:
                with open(file_record.path, "rb") as f:
                    # 최소한 1바이트라도 읽을 수 있는지 확인
                    f.read(1)
            except (OSError, PermissionError) as e:
                return IntegrityIssue(
                    path=file_record.path,
                    code=INTEGRITY_ISSUE_CODE_READ_ERROR,
                    severity="ERROR",
                    message=f"파일 읽기 실패: {str(e)}",
                    meta={"error": str(e)}
                )
            
            return None
            
        except Exception as e:
            # 예상치 못한 오류
            self._logger.warning(f"파일 접근성 검사 중 오류: {file_record.path} - {e}")
            return IntegrityIssue(
                path=file_record.path,
                code=INTEGRITY_ISSUE_CODE_READ_ERROR,
                severity="ERROR",
                message=f"접근성 검사 중 오류: {str(e)}",
                meta={"error": str(e)}
            )
    
    def _check_decode_sample(self, file_record: FileRecord) -> Optional[IntegrityIssue]:
        """디코딩 검증을 수행합니다.
        
        감지된 인코딩으로 실제로 파일을 디코딩할 수 있는지 확인합니다.
        샘플만 읽어서 검증하므로 대용량 파일도 빠르게 처리됩니다.
        
        BOM 처리를 포함하여 실제 텍스트 에디터와 유사한 방식으로 검증합니다.
        
        Args:
            file_record: 검사할 FileRecord
        
        Returns:
            디코딩 실패 시 IntegrityIssue, 성공 시 None
        """
        try:
            # 인코딩 정보 확인
            encoding = file_record.encoding
            
            # 인코딩이 감지되지 않았거나 빈 파일인 경우
            if encoding in (ENCODING_NOT_DETECTED, ENCODING_EMPTY, "-", ENCODING_UNKNOWN, ENCODING_NA):
                # 기본 인코딩으로 시도
                encoding = DEFAULT_ENCODING
                self._logger.debug(
                    f"인코딩 미감지, 기본값 사용: {file_record.path} -> {encoding}"
                )
            
            # 샘플 읽기 및 디코딩 시도
            try:
                with open(file_record.path, "rb") as f:
                    sample = f.read(INTEGRITY_DECODE_SAMPLE_SIZE)
                
                # 빈 파일은 이미 _check_empty_file에서 처리됨
                if len(sample) == 0:
                    return None
                
                # UTF-8 BOM 처리 (BOM이 있으면 제거)
                if encoding.lower() in ("utf-8", "utf8") and sample.startswith(b"\xef\xbb\xbf"):
                    sample = sample[3:]
                
                # UTF-16 BOM 처리
                if encoding.lower() in ("utf-16", "utf-16le", "utf-16be"):
                    if sample.startswith(b"\xff\xfe"):
                        sample = sample[2:]
                        encoding = "utf-16-le"
                    elif sample.startswith(b"\xfe\xff"):
                        sample = sample[2:]
                        encoding = "utf-16-be"
                
                # 먼저 strict 모드로 시도
                try:
                    sample.decode(encoding, errors="strict")
                    return None
                except UnicodeDecodeError as strict_error:
                    # strict 모드 실패 시, replace 모드로 재시도하여 실제로 읽을 수 있는지 확인
                    # replace 모드로 성공하면 파일은 읽을 수 있지만 일부 문자가 깨져있을 수 있음
                    try:
                        decoded = sample.decode(encoding, errors="replace")
                        # replacement character (\ufffd)가 있는지 확인
                        replacement_count = decoded.count("\ufffd")
                        total_chars = len(decoded)
                        
                        # replacement character 비율이 높으면 (5% 이상) 문제로 간주
                        if replacement_count > 0 and total_chars > 0:
                            replacement_ratio = replacement_count / total_chars
                            if replacement_ratio > 0.05:  # 5% 이상
                                self._logger.warning(
                                    f"디코딩 문제 발견: {file_record.path} - "
                                    f"replacement character {replacement_count}/{total_chars} "
                                    f"({replacement_ratio:.1%})"
                                )
                                return IntegrityIssue(
                                    path=file_record.path,
                                    code=INTEGRITY_ISSUE_CODE_DECODE_ERROR,
                                    severity="WARN",  # ERROR에서 WARN으로 변경 (읽을 수는 있음)
                                    message=f"디코딩 문제 ({encoding}): 일부 문자가 깨져있음",
                                    meta={
                                        "encoding": encoding,
                                        "error": str(strict_error),
                                        "replacement_ratio": replacement_ratio,
                                        "position": strict_error.start if hasattr(strict_error, "start") else None
                                    }
                                )
                        # replacement character가 적으면 (5% 미만) 정상으로 간주
                        # 실제 텍스트 에디터도 이런 방식으로 처리함
                        return None
                    except Exception:
                        # replace 모드로도 실패하면 진짜 문제
                        raise strict_error
                
            except UnicodeDecodeError as e:
                # 디코딩 실패 (replace 모드로도 실패)
                self._logger.warning(
                    f"디코딩 실패: {file_record.path} - 인코딩: {encoding}, 오류: {e}"
                )
                return IntegrityIssue(
                    path=file_record.path,
                    code=INTEGRITY_ISSUE_CODE_DECODE_ERROR,
                    severity="ERROR",
                    message=f"디코딩 실패 ({encoding})",
                    meta={
                        "encoding": encoding,
                        "error": str(e),
                        "position": e.start if hasattr(e, "start") else None
                    }
                )
            except LookupError as e:
                # 알 수 없는 인코딩
                self._logger.warning(
                    f"알 수 없는 인코딩: {file_record.path} - {encoding}"
                )
                return IntegrityIssue(
                    path=file_record.path,
                    code=INTEGRITY_ISSUE_CODE_DECODE_ERROR,
                    severity="ERROR",
                    message=f"알 수 없는 인코딩: {encoding}",
                    meta={
                        "encoding": encoding,
                        "error": str(e)
                    }
                )
            
        except Exception as e:
            # 예상치 못한 오류
            self._logger.warning(f"디코딩 검증 중 오류: {file_record.path} - {e}", exc_info=True)
            return IntegrityIssue(
                path=file_record.path,
                code=INTEGRITY_ISSUE_CODE_DECODE_ERROR,
                severity="ERROR",
                message=f"디코딩 검증 중 오류: {str(e)}",
                meta={"error": str(e)}
            )

