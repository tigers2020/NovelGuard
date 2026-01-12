"""로그 싱크 Port 인터페이스."""
from typing import Protocol

from application.dto.log_entry import LogEntry


class ILogSink(Protocol):
    """로그 싱크 인터페이스.
    
    로그를 기록하는 인터페이스.
    Infrastructure 계층에서 구현해야 함.
    """
    
    def write(self, entry: LogEntry) -> None:
        """로그 엔트리 기록.
        
        Args:
            entry: 로그 엔트리.
        """
        ...
