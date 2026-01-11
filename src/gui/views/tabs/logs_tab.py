"""작업 로그 탭."""
from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class LogsTab(BaseTab):
    """작업 로그 탭."""
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📝 작업 로그"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 로그 콘솔
        log_group = self._create_log_group()
        layout.addWidget(log_group)
    
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
        self._log_console.setPlainText("로그가 여기에 표시됩니다...")
        layout.addWidget(self._log_console)
        
        # 샘플 로그 추가
        self._add_sample_logs()
        
        return group
    
    def _add_sample_logs(self) -> None:
        """샘플 로그 추가."""
        logs = [
            "[14:23:45] [INFO] 스캔 시작",
            "[14:23:46] [INFO] 워커 스레드 8개 초기화",
            "[14:24:45] [WARN] 인코딩 감지 실패",
            "[14:25:45] [ERROR] 파일 읽기 실패",
        ]
        
        for log in logs:
            self._log_console.appendPlainText(log)
    
    def _on_clear_logs(self) -> None:
        """로그 지우기 핸들러."""
        self._log_console.clear()
        self._log_console.appendPlainText("로그가 지워졌습니다.")
    
    def _on_export_logs(self) -> None:
        """로그 내보내기 핸들러."""
        # TODO: 실제 로그 내보내기 구현
        print("로그 내보내기")
