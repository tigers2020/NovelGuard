"""인메모리 로그 싱크 구현."""
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink


class InMemoryLogSink(QObject):
    """인메모리 로그 싱크 - ILogSink 구현.
    
    최근 N개 로그를 메모리에 저장하고 Qt Signal으로 GUI에 알림.
    
    ILogSink Protocol을 구현 (구조적 서브타이핑, 상속 불필요).
    """
    
    log_added = Signal(LogEntry)
    """로그 추가 시그널 (GUI에서 실시간 업데이트용)."""
    
    # 최대 로그 개수
    MAX_LOGS = 10000
    
    def __init__(self, parent: Optional[QObject] = None, log_dir: Optional[Path] = None) -> None:
        """인메모리 로그 싱크 초기화.
        
        Args:
            parent: 부모 객체.
            log_dir: 로그 파일 저장 디렉토리 (None이면 프로젝트 루트/logs 사용).
        """
        super().__init__(parent)
        # 순환 버퍼 (deque 사용)
        self._logs: deque[LogEntry] = deque(maxlen=self.MAX_LOGS)
        
        # 로그 디렉토리 설정
        if log_dir is None:
            # 프로젝트 루트 찾기
            try:
                import sys
                if hasattr(sys, 'frozen'):  # PyInstaller로 빌드된 경우
                    # 실행 파일이 있는 디렉토리
                    base_path = Path(sys.executable).parent
                else:
                    # src/infrastructure/logging/in_memory_log_sink.py에서 실행되는 경우
                    # __file__ = src/infrastructure/logging/in_memory_log_sink.py
                    # parent.parent.parent = src/
                    # parent.parent.parent.parent = 프로젝트 루트
                    current_file = Path(__file__)
                    # src/infrastructure/logging -> infrastructure -> src -> 프로젝트 루트
                    base_path = current_file.parent.parent.parent.parent
            except Exception:
                # 실패 시 현재 작업 디렉토리 사용
                base_path = Path.cwd()
            
            self._log_dir = base_path / "logs"
        else:
            self._log_dir = Path(log_dir)
        
        # 로그 디렉토리 생성
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # 현재 날짜 로그 파일 경로
        self._current_log_file: Optional[Path] = None
        self._current_date: Optional[str] = None
    
    def write(self, entry: LogEntry) -> None:
        """로그 엔트리 기록.
        
        Args:
            entry: 로그 엔트리.
        """
        # 타임스탬프가 없으면 현재 시간 사용
        if not hasattr(entry, 'timestamp') or entry.timestamp is None:
            entry.timestamp = datetime.now()
        
        self._logs.append(entry)
        self.log_added.emit(entry)
        
        # PowerShell 콘솔에도 출력
        self._print_to_console(entry)
        
        # 로그 파일에도 저장
        self._write_to_file(entry)
    
    def get_logs(
        self,
        job_id: Optional[int] = None,
        level: Optional[str] = None
    ) -> list[LogEntry]:
        """로그 목록 조회.
        
        Args:
            job_id: Job ID 필터 (선택적).
            level: 로그 레벨 필터 (선택적).
        
        Returns:
            필터링된 로그 엔트리 리스트.
        """
        logs = list(self._logs)
        
        # 필터링
        if job_id is not None:
            logs = [log for log in logs if log.job_id == job_id]
        
        if level is not None:
            logs = [log for log in logs if log.level == level]
        
        return logs
    
    def _print_to_console(self, entry: LogEntry) -> None:
        """콘솔에 로그 출력 (PowerShell용).
        
        Args:
            entry: 로그 엔트리.
        """
        timestamp_str = entry.timestamp.strftime("%H:%M:%S")
        level_str = entry.level
        message_str = entry.message
        
        # Job ID가 있으면 표시
        job_id_str = f" [Job:{entry.job_id}]" if entry.job_id is not None else ""
        
        # Context 정보가 있으면 표시
        context_str = ""
        if entry.context:
            try:
                # Context를 JSON 형식으로 포맷팅 (한 줄로)
                context_json = json.dumps(entry.context, ensure_ascii=False, separators=(',', ':'))
                # 너무 길면 잘라내기
                if len(context_json) > 200:
                    context_json = context_json[:197] + "..."
                context_str = f" | {context_json}"
            except (TypeError, ValueError):
                # JSON 변환 실패 시 문자열로 표시
                context_str = f" | {str(entry.context)[:200]}"
        
        log_line = f"[{timestamp_str}] [{level_str}]{job_id_str} {message_str}{context_str}"
        
        # 레벨에 따라 색상 구분 (PowerShell ANSI 색상 코드)
        if level_str == "ERROR":
            # 빨간색
            print(f"\033[91m{log_line}\033[0m")
        elif level_str == "WARNING":
            # 노란색
            print(f"\033[93m{log_line}\033[0m")
        elif level_str == "INFO":
            # 파란색
            print(f"\033[94m{log_line}\033[0m")
        elif level_str == "DEBUG":
            # 회색
            print(f"\033[90m{log_line}\033[0m")
        else:
            # 기본 색상
            print(log_line)
    
    def _write_to_file(self, entry: LogEntry) -> None:
        """로그 파일에 저장.
        
        Args:
            entry: 로그 엔트리.
        """
        try:
            # 날짜별 로그 파일 (YYYY-MM-DD.log)
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            
            # 날짜가 바뀌었으면 새 파일 경로 설정
            if self._current_date != date_str:
                self._current_date = date_str
                self._current_log_file = self._log_dir / f"{date_str}.log"
            
            # 로그 라인 포맷팅 (파일용 - 색상 코드 제외)
            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 밀리초 포함
            level_str = entry.level
            message_str = entry.message
            
            # Job ID가 있으면 표시
            job_id_str = f" [Job:{entry.job_id}]" if entry.job_id is not None else ""
            
            # Context 정보가 있으면 표시
            context_str = ""
            if entry.context:
                try:
                    # Context를 JSON 형식으로 포맷팅 (한 줄로)
                    context_json = json.dumps(entry.context, ensure_ascii=False, separators=(',', ':'))
                    context_str = f" | {context_json}"
                except (TypeError, ValueError):
                    # JSON 변환 실패 시 문자열로 표시
                    context_str = f" | {str(entry.context)}"
            
            log_line = f"[{timestamp_str}] [{level_str}]{job_id_str} {message_str}{context_str}\n"
            
            # 파일에 추가 (append 모드)
            if self._current_log_file:
                with open(self._current_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
        except Exception as e:
            # 파일 쓰기 실패 시 콘솔에만 에러 출력 (무한 루프 방지)
            print(f"[ERROR] 로그 파일 쓰기 실패: {e}")
