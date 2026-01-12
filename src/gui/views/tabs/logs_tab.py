"""작업 로그 탭."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from gui.views.tabs.base_tab import BaseTab


class LogsTab(BaseTab):
    """작업 로그 탭."""
    
    def __init__(
        self,
        parent=None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """로그 탭 초기화.
        
        Args:
            parent: 부모 위젯.
            log_sink: 로그 싱크 (선택적).
        """
        self._log_sink = log_sink
        super().__init__(parent)
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📝 작업 로그"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 필터 바
        filter_bar = self._create_filter_bar()
        layout.addLayout(filter_bar)
        
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 로그 콘솔
        log_group = self._create_log_group()
        layout.addWidget(log_group)
        
        # LogSink 연결 (실시간 업데이트)
        if self._log_sink:
            # InMemoryLogSink의 log_added 시그널 연결
            if hasattr(self._log_sink, 'log_added'):
                self._log_sink.log_added.connect(self._on_log_added)
            # 기존 로그 로드
            self._load_existing_logs()
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """필터 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        # 레벨 필터
        level_label = QLabel("레벨:")
        layout.addWidget(level_label)
        
        self._level_filter = QComboBox()
        self._level_filter.addItems(["모두", "DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_filter.setCurrentText("모두")  # 기본값을 "모두"로 설정
        self._level_filter.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self._level_filter)
        
        layout.addStretch()
        
        return layout
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        clear_btn = QPushButton("로그 지우기")
        clear_btn.setObjectName("btnSecondary")
        clear_btn.clicked.connect(self._on_clear_logs)
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("로그 내보내기")
        export_btn.setObjectName("btnSecondary")
        export_btn.clicked.connect(self._on_export_logs)
        layout.addWidget(export_btn)
        
        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("btnSecondary")
        refresh_btn.clicked.connect(self._load_existing_logs)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        return layout
    
    def _create_log_group(self) -> QGroupBox:
        """로그 그룹 생성."""
        group = QGroupBox("실시간 로그")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        
        # 로그 콘솔
        self._log_console = QPlainTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d0d0d;
                color: #d4d4d4;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self._log_console.setPlainText("로그가 여기에 표시됩니다...\n")
        layout.addWidget(self._log_console)
        
        return group
    
    def _format_log_entry(self, entry: LogEntry) -> str:
        """로그 엔트리를 문자열로 포맷팅.
        
        Args:
            entry: 로그 엔트리.
        
        Returns:
            포맷팅된 로그 문자열.
        """
        timestamp_str = entry.timestamp.strftime("%H:%M:%S")
        level_str = entry.level
        message_str = entry.message
        
        # Job ID가 있으면 표시
        job_id_str = f" [Job:{entry.job_id}]" if entry.job_id is not None else ""
        
        # Context 정보가 있으면 표시
        context_str = ""
        if entry.context:
            import json
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
        
        return f"[{timestamp_str}] [{level_str}]{job_id_str} {message_str}{context_str}"
    
    def _on_log_added(self, entry: LogEntry) -> None:
        """로그 추가 시그널 핸들러 (실시간 업데이트).
        
        Args:
            entry: 추가된 로그 엔트리.
        """
        # _level_filter가 아직 생성되지 않았으면 무시 (초기화 중)
        if not hasattr(self, '_level_filter') or self._level_filter is None:
            return
        
        # 필터 확인
        level_filter = self._level_filter.currentText()
        if level_filter != "모두" and entry.level != level_filter:
            return
        
        # _log_console이 아직 생성되지 않았으면 무시 (초기화 중)
        if not hasattr(self, '_log_console') or self._log_console is None:
            return
        
        # 로그 추가
        log_line = self._format_log_entry(entry)
        self._log_console.appendPlainText(log_line)
        
        # 자동 스크롤 (맨 아래로)
        scrollbar = self._log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 디버깅 로그는 중복 방지를 위해 여기서는 로깅하지 않음 (무한 루프 방지)
    
    def _load_existing_logs(self) -> None:
        """기존 로그 로드."""
        if not self._log_sink or not hasattr(self._log_sink, 'get_logs'):
            if hasattr(self, '_log_console') and self._log_console:
                self._log_console.appendPlainText("로그 싱크가 연결되지 않았습니다.")
            return
        
        # 필터 확인 (_level_filter가 생성되지 않았으면 "모두"로 가정)
        if hasattr(self, '_level_filter') and self._level_filter:
            level_filter = self._level_filter.currentText()
            level = None if level_filter == "모두" else level_filter
        else:
            level = None  # 필터가 없으면 모든 로그 표시
        
        # 로그 가져오기
        logs = self._log_sink.get_logs(level=level)
        
        # 콘솔 클리어 및 로그 추가
        if hasattr(self, '_log_console') and self._log_console:
            self._log_console.clear()
            if not logs:
                self._log_console.appendPlainText(f"로그가 없습니다. (필터: {level_filter if hasattr(self, '_level_filter') and self._level_filter else '모두'})")
            else:
                self._log_console.appendPlainText(f"총 {len(logs)}개의 로그를 불러왔습니다.\n")
                for entry in logs:
                    log_line = self._format_log_entry(entry)
                    self._log_console.appendPlainText(log_line)
            
            # 자동 스크롤 (맨 아래로)
            scrollbar = self._log_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _on_filter_changed(self, text: str) -> None:
        """필터 변경 핸들러.
        
        Args:
            text: 선택된 필터 텍스트.
        """
        # 디버깅 로그는 중복 방지를 위해 여기서는 로깅하지 않음
        self._load_existing_logs()
    
    def _on_clear_logs(self) -> None:
        """로그 지우기 핸들러."""
        self._log_console.clear()
        self._log_console.appendPlainText("로그 화면이 지워졌습니다. (실제 로그는 유지됩니다.)\n")
    
    def _on_export_logs(self) -> None:
        """로그 내보내기 핸들러."""
        # TODO: 실제 로그 내보내기 구현 (파일 다이얼로그)
        print("로그 내보내기")
