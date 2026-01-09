"""UIBatcher - 배치 큐 + 플러시 타이머."""

from typing import Optional
from PySide6.QtCore import QObject, QTimer
from gui.view_models.file_row import FileRow
from common.logging import setup_logging

logger = setup_logging()


class UIBatcher(QObject):
    """UI 배치 처리기.
    
    Worker 신호를 큐에 적재하고 주기적으로 모델에 반영.
    """
    
    # 정책 상수
    MAX_APPEND_CHUNK = 1000  # rows
    MAX_UPDATE_CHUNK = 500  # rows
    FLUSH_INTERVAL_MS = 16  # ms (60fps)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """UIBatcher 초기화.
        
        Args:
            parent: 부모 객체
        """
        super().__init__(parent)
        
        # 큐
        self._append_queue: list[FileRow] = []
        self._update_queue: list[FileRow] = []
        
        # 타이머
        self._timer = QTimer(self)
        self._timer.setInterval(self.FLUSH_INTERVAL_MS)
        self._timer.timeout.connect(self._flush)
    
    def enqueue_append(self, rows: list[FileRow]) -> None:
        """추가할 행들을 큐에 적재.
        
        Args:
            rows: 추가할 FileRow 리스트
        """
        self._append_queue.extend(rows)
        
        if not self._timer.isActive():
            self._timer.start()
    
    def enqueue_update(self, rows: list[FileRow]) -> None:
        """업데이트할 행들을 큐에 적재.
        
        Args:
            rows: 업데이트할 FileRow 리스트
        """
        self._update_queue.extend(rows)
        
        if not self._timer.isActive():
            self._timer.start()
    
    def _flush(self) -> None:
        """큐에서 배치를 꺼내서 처리."""
        # Append 우선 처리
        if self._append_queue:
            chunk = self._append_queue[:self.MAX_APPEND_CHUNK]
            self._append_queue = self._append_queue[self.MAX_APPEND_CHUNK:]
            self.rows_appended.emit(chunk)
        
        # Update 처리
        if self._update_queue:
            chunk = self._update_queue[:self.MAX_UPDATE_CHUNK]
            self._update_queue = self._update_queue[self.MAX_UPDATE_CHUNK:]
            self.rows_updated.emit(chunk)
        
        # 큐가 비면 타이머 중지
        if not self._append_queue and not self._update_queue:
            self._timer.stop()
    
    # Signals (호출자에서 연결)
    rows_appended = Signal(list)  # list[FileRow]
    rows_updated = Signal(list)  # list[FileRow]

