"""통계 및 리포트 탭."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from app.settings.constants import Constants
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from gui.view_models.stats_view_model import StatsViewModel
from gui.views.tabs.base_tab import BaseTab


class StatsTab(BaseTab):
    """통계 및 리포트 탭."""
    
    def __init__(
        self,
        parent=None,
        index_repo: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """통계 탭 초기화.
        
        Args:
            parent: 부모 위젯.
            index_repo: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        self._index_repo = index_repo
        self._log_sink = log_sink
        
        # ViewModel을 먼저 생성 (_setup_content에서 참조할 수 있도록)
        # parent가 없으면 일단 None으로 생성하고, super().__init__ 이후에 parent 설정
        self._view_model = StatsViewModel(parent=None, index_repo=index_repo, log_sink=log_sink)
        
        super().__init__(parent)
        
        # ViewModel의 parent 설정 (super().__init__ 이후)
        self._view_model.setParent(self)
        self._connect_view_model_signals()
        
        # 초기 데이터 로드
        self._view_model.load_data()
    
    def _connect_view_model_signals(self) -> None:
        """ViewModel 시그널 연결."""
        self._view_model.data_changed.connect(self._on_data_changed)
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📊 통계 및 리포트"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # Run 요약 카드
        run_summary_card = self._create_run_summary_card()
        layout.addWidget(run_summary_card)
        
        # 확장자 분포 및 큰 파일 (좌우 분할)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)
        
        # 확장자 분포
        ext_distribution_group = self._create_ext_distribution_group()
        bottom_layout.addWidget(ext_distribution_group, stretch=1)
        
        # 큰 파일 Top N
        top_files_group = self._create_top_files_group()
        bottom_layout.addWidget(top_files_group, stretch=1)
        
        layout.addLayout(bottom_layout)
    
    def _create_run_summary_card(self) -> QGroupBox:
        """Run 요약 카드 생성."""
        group = QGroupBox("최신 스캔 정보")
        group.setObjectName("settingsGroup")
        
        layout = QHBoxLayout(group)
        layout.setSpacing(16)
        
        # 파일 수
        self._total_files_card = self._create_stat_card("총 파일 수", "0", "개", "#6366f1")
        layout.addWidget(self._total_files_card)
        
        # 총 용량
        self._total_bytes_card = self._create_stat_card("총 용량", "0", "bytes", "#43e97b")
        layout.addWidget(self._total_bytes_card)
        
        # 경과 시간
        self._elapsed_time_card = self._create_stat_card("경과 시간", "0", "ms", "#f093fb")
        layout.addWidget(self._elapsed_time_card)
        
        return group
    
    def _create_ext_distribution_group(self) -> QGroupBox:
        """확장자별 분포 그룹 생성."""
        group = QGroupBox("확장자별 분포 (Top 10)")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        
        # 리스트 위젯
        self._ext_list = QListWidget()
        self._ext_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidgetItem {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidgetItem:hover {
                background-color: #252525;
            }
        """)
        layout.addWidget(self._ext_list)
        
        return group
    
    def _create_top_files_group(self) -> QGroupBox:
        """큰 파일 Top N 그룹 생성."""
        group = QGroupBox("큰 파일 Top 50")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        
        # 리스트 위젯
        self._top_files_list = QListWidget()
        self._top_files_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidgetItem {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidgetItem:hover {
                background-color: #252525;
            }
        """)
        layout.addWidget(self._top_files_list)
        
        return group
    
    def _format_file_size(self, size_bytes: int) -> str:
        """파일 크기를 읽기 쉬운 형식으로 포맷팅.
        
        Args:
            size_bytes: 바이트 수.
        
        Returns:
            포맷팅된 크기 문자열.
        """
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size_bytes < float(Constants.BYTES_PER_KB):
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= float(Constants.BYTES_PER_KB)
        return f"{size_bytes:.1f} TB"
    
    def _on_data_changed(self) -> None:
        """데이터 변경 시그널 핸들러."""
        self._update_run_summary()
        self._update_ext_distribution()
        self._update_top_files()
    
    def _update_run_summary(self) -> None:
        """Run 요약 업데이트."""
        summary = self._view_model.latest_run_summary
        if summary:
            # 총 파일 수
            self._update_stat_card(self._total_files_card, str(summary.total_files), "개")
            
            # 총 용량
            size_str = self._format_file_size(summary.total_bytes)
            self._update_stat_card(self._total_bytes_card, size_str, "")
            
            # 경과 시간
            elapsed_sec = summary.elapsed_ms / float(Constants.MILLISECONDS_PER_SECOND)
            if elapsed_sec < 1:
                time_str = f"{summary.elapsed_ms}ms"
            else:
                time_str = f"{elapsed_sec:.1f}초"
            self._update_stat_card(self._elapsed_time_card, time_str, "")
        else:
            self._update_stat_card(self._total_files_card, "0", "개")
            self._update_stat_card(self._total_bytes_card, "0", "bytes")
            self._update_stat_card(self._elapsed_time_card, "0", "ms")
    
    def _update_stat_card(self, card: QGroupBox, value: str, unit: str) -> None:
        """통계 카드 값 업데이트.
        
        Args:
            card: 통계 카드 위젯.
            value: 값 문자열.
            unit: 단위 문자열.
        """
        # 카드의 레이아웃에서 value_widget과 unit_widget 찾기
        layout = card.layout()
        if layout:
            # value_widget (인덱스 1), unit_widget (인덱스 2, 있으면)
            if layout.count() > 1:
                value_widget = layout.itemAt(1).widget()
                if isinstance(value_widget, QLabel):
                    value_widget.setText(value)
            
            if layout.count() > 2 and unit:
                unit_widget = layout.itemAt(2).widget()
                if isinstance(unit_widget, QLabel):
                    unit_widget.setText(unit)
                    unit_widget.setVisible(bool(unit))
    
    def _update_ext_distribution(self) -> None:
        """확장자 분포 업데이트."""
        self._ext_list.clear()
        
        distribution = self._view_model.ext_distribution[:10]  # Top 10
        
        if not distribution:
            item = QListWidgetItem("(데이터 없음)")
            item.setForeground(Qt.GlobalColor.gray)
            self._ext_list.addItem(item)
            return
        
        for ext_stat in distribution:
            ext_name = ext_stat.ext if ext_stat.ext else "(확장자 없음)"
            count = ext_stat.count
            total_bytes = self._format_file_size(ext_stat.total_bytes)
            text = f"{ext_name}: {count}개 파일, {total_bytes}"
            item = QListWidgetItem(text)
            self._ext_list.addItem(item)
    
    def _update_top_files(self) -> None:
        """큰 파일 Top N 업데이트."""
        self._top_files_list.clear()
        
        top_files = self._view_model.top_files
        
        if not top_files:
            item = QListWidgetItem("(데이터 없음)")
            item.setForeground(Qt.GlobalColor.gray)
            self._top_files_list.addItem(item)
            return
        
        for file_entry in top_files:
            file_name = file_entry.path.name
            size_str = self._format_file_size(file_entry.size)
            text = f"{file_name} ({size_str})"
            item = QListWidgetItem(text)
            item.setToolTip(str(file_entry.path))  # 전체 경로를 툴팁으로
            self._top_files_list.addItem(item)
    
    def _create_stat_card(self, label: str, value: str, unit: Optional[str], color: str) -> QGroupBox:
        """통계 카드 생성."""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}dd);
                border: none;
                border-radius: 12px;
                padding: 20px;
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("background: transparent; font-size: 13px; opacity: 0.9; color: white;")
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet("background: transparent; font-size: 32px; font-weight: 700; color: white;")
        layout.addWidget(value_widget)
        
        if unit:
            unit_widget = QLabel(unit)
            unit_widget.setStyleSheet("background: transparent; font-size: 14px; opacity: 0.9; color: white;")
            layout.addWidget(unit_widget)
        
        return card
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("btnSecondary")
        refresh_btn.clicked.connect(self._view_model.refresh)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        return layout
