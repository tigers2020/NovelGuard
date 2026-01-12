"""파일 스캔 탭."""
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.dto.scan_result import ScanResult
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from application.utils.scan_json import generate_scan_json_filename, save_scan_result_to_json
from gui.models.app_state import AppState
from gui.view_models.scan_view_model import ScanViewModel
from gui.views.tabs.base_tab import BaseTab

logger = logging.getLogger(__name__)


class ScanTab(BaseTab):
    """파일 스캔 탭."""
    
    folder_selected = Signal(Path)
    """폴더 선택 시그널."""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager=None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """스캔 탭 초기화.
        
        Args:
            parent: 부모 위젯.
            job_manager: Job 관리자 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        self._scan_folder: Optional[Path] = None
        self._log_sink = log_sink
        super().__init__(parent)
        
        debug_step(self._log_sink, "scan_tab_init")
        
        # AppState 가져오기
        self._app_state = self._get_app_state()
        
        # ViewModel 생성 (job_manager, log_sink 전달)
        self._view_model = ScanViewModel(self, job_manager=job_manager, log_sink=log_sink)
        self._connect_view_model_signals()
    
    def _get_app_state(self) -> AppState:
        """AppState 가져오기."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_app_state'):
                return parent._app_state
            parent = parent.parent()
        # 기본값으로 새로 생성 (일반적으로는 발생하지 않음)
        return AppState()
    
    def _connect_view_model_signals(self) -> None:
        """ViewModel 시그널 연결."""
        self._view_model.progress_updated.connect(self._on_progress_updated)
        self._view_model.scan_completed.connect(self._on_scan_completed)
        self._view_model.scan_error.connect(self._on_scan_error)
        self._view_model.error_occurred.connect(self._on_error_occurred)
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "📁 파일 스캔"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 대상 폴더 그룹
        folder_group = self._create_folder_group()
        layout.addWidget(folder_group)
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        # 폴더 선택 버튼
        folder_btn = QPushButton("📂 폴더 선택")
        folder_btn.setObjectName("btnPrimary")
        folder_btn.clicked.connect(self._on_select_folder)
        layout.addWidget(folder_btn)
        
        # 스캔 시작 버튼
        scan_btn = QPushButton("▶ 스캔 시작")
        scan_btn.setObjectName("btnPrimary")
        scan_btn.clicked.connect(self._on_start_scan)
        layout.addWidget(scan_btn)
        
        # 중지 버튼
        stop_btn = QPushButton("중지")
        stop_btn.setObjectName("btnSecondary")
        stop_btn.clicked.connect(self._on_stop_scan)
        layout.addWidget(stop_btn)
        
        layout.addStretch()
        
        return layout
    
    def _create_progress_section(self) -> QGroupBox:
        """프로그레스 섹션 생성."""
        group = QGroupBox()
        group.setTitle("")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 프로그레스 헤더
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        
        progress_title = QLabel("스캔 진행 중...")
        progress_title.setObjectName("progressTitle")
        progress_header.addWidget(progress_title)
        
        progress_header.addStretch()
        
        self._progress_percent = QLabel("0%")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)
        
        layout.addLayout(progress_header)
        
        # 프로그레스 바
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)
        
        # 프로그레스 정보
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        self._progress_info.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self._progress_info)
        
        # 항상 보이도록 설정
        group.setVisible(True)
        
        return group
    
    def _create_folder_group(self) -> QGroupBox:
        """대상 폴더 그룹 생성."""
        group = QGroupBox("대상 폴더")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        folder_layout = QVBoxLayout()
        folder_layout.setSpacing(8)
        
        folder_label = QLabel("스캔할 폴더를 선택하세요")
        folder_label.setObjectName("formLabel")
        folder_layout.addWidget(folder_label)
        
        self._folder_input = QLineEdit()
        self._folder_input.setReadOnly(True)
        self._folder_input.setPlaceholderText("폴더를 선택하세요")
        folder_layout.addWidget(self._folder_input)
        
        layout.addLayout(folder_layout)
        
        return group
    
    def _on_select_folder(self) -> None:
        """폴더 선택 핸들러."""
        debug_step(self._log_sink, "scan_tab_select_folder")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "스캔할 폴더 선택",
            str(self._scan_folder) if self._scan_folder else ""
        )
        
        if folder:
            folder_path = Path(folder)
            debug_step(self._log_sink, "scan_tab_folder_selected", {"folder": str(folder_path)})
            self.set_scan_folder(folder_path)
            # 시그널 emit하여 MainWindow가 preview scan을 시작하도록
            self.folder_selected.emit(folder_path)
    
    def set_scan_folder(self, folder: Path) -> None:
        """스캔 폴더 설정.
        
        Args:
            folder: 설정할 폴더 경로.
        """
        self._scan_folder = folder
        self._folder_input.setText(str(self._scan_folder))
    
    def get_scan_folder(self) -> Optional[Path]:
        """스캔 폴더 반환.
        
        Returns:
            현재 설정된 스캔 폴더. 없으면 None.
        """
        return self._scan_folder
    
    def _get_settings_tab(self):
        """SettingsTab 위젯 반환."""
        # MainWindow를 찾아서 SettingsTab 가져오기
        parent = self.parent()
        while parent:
            if hasattr(parent, '_get_settings_tab'):
                return parent._get_settings_tab()
            parent = parent.parent()
        return None
    
    def get_extension_filter(self) -> str:
        """확장자 필터 반환.
        
        Returns:
            확장자 필터 문자열 (예: ".txt, .md, .log").
        """
        settings_tab = self._get_settings_tab()
        if settings_tab:
            return settings_tab.get_extension_filter()
        return ""
    
    def get_include_subdirs(self) -> bool:
        """하위 폴더 포함 여부 반환.
        
        Returns:
            하위 폴더 포함 여부.
        """
        settings_tab = self._get_settings_tab()
        if settings_tab:
            return settings_tab.get_include_subdirs()
        return True  # 기본값
    
    def get_include_hidden(self) -> bool:
        """숨김 파일 포함 여부 반환.
        
        Returns:
            숨김 파일 포함 여부.
        """
        settings_tab = self._get_settings_tab()
        if settings_tab:
            return settings_tab.get_include_hidden()
        return False  # 기본값
    
    def get_include_symlinks(self) -> bool:
        """심볼릭 링크 포함 여부 반환.
        
        Returns:
            심볼릭 링크 포함 여부.
        """
        settings_tab = self._get_settings_tab()
        if settings_tab:
            return settings_tab.get_include_symlinks()
        return True  # 기본값
    
    def get_incremental_scan(self) -> bool:
        """증분 스캔 여부 반환.
        
        Returns:
            증분 스캔 여부.
        """
        settings_tab = self._get_settings_tab()
        if settings_tab:
            return settings_tab.get_incremental_scan()
        return True  # 기본값
    
    def _on_progress_updated(self, progress: int, message: str) -> None:
        """진행률 업데이트 핸들러."""
        # Indeterminate 진행률: progress는 항상 0 (의미 없음)
        # 프로그레스 바를 indeterminate 모드로 설정
        self._progress_bar.setRange(0, 0)  # indeterminate 모드
        
        # count 정보 표시
        count = self._view_model.progress_count
        if count > 0:
            self._progress_info.setText(f"{message} ({count}개 파일)")
        else:
            self._progress_info.setText(message)
        
        # 프로그레스 퍼센트 라벨 숨기기 (indeterminate이므로 의미 없음)
        self._progress_percent.setText("")
    
    def _on_scan_completed(self, result: ScanResult) -> None:
        """스캔 완료 핸들러."""
        debug_step(
            self._log_sink,
            "scan_tab_scan_completed",
            {
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
                "elapsed_ms": result.elapsed_ms,
            }
        )
        
        # 프로그레스 바를 normal 모드로 복원
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._progress_info.setText(f"완료: {result.total_files}개 파일, {result.total_bytes:,} bytes")
        
        # 공유 데이터 저장소에 파일 추가
        if result.entries:
            data_store = self._app_state.file_data_store
            # 스캔 폴더 설정
            if self._scan_folder:
                data_store.scan_folder = self._scan_folder
            # 파일 추가
            data_store.add_files(result.entries)
        
        # JSON 파일로 저장
        self._save_scan_result_to_json(result)
    
    def _on_scan_error(self, error_message: str) -> None:
        """스캔 오류 핸들러."""
        # 프로그레스 바를 normal 모드로 복원
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_percent.setText("")
        self._progress_info.setText(f"오류: {error_message}")
        # TODO: 오류 메시지 표시 (로그 탭 등)
    
    def _on_error_occurred(self, error_message: str) -> None:
        """일반 오류 핸들러."""
        self._progress_info.setText(f"오류: {error_message}")
    
    def _on_start_scan(self) -> None:
        """스캔 시작 핸들러."""
        debug_step(
            self._log_sink,
            "scan_tab_start_scan",
            {
                "scan_folder": str(self._scan_folder) if self._scan_folder else None,
                "extensions": self.get_extension_filter(),
            }
        )
        
        if not self._scan_folder:
            # TODO: 에러 메시지 표시
            return
        
        # ViewModel 호출
        self._view_model.start_scan(
            folder=self._scan_folder,
            extensions=self.get_extension_filter(),
            include_subdirs=self.get_include_subdirs(),
            include_hidden=self.get_include_hidden(),
            include_symlinks=self.get_include_symlinks(),
            incremental_scan=self.get_incremental_scan(),
        )
    
    def _on_stop_scan(self) -> None:
        """스캔 중지 핸들러."""
        debug_step(self._log_sink, "scan_tab_stop_scan")
        self._view_model.stop_scan()
    
    def _save_scan_result_to_json(self, result: ScanResult) -> None:
        """스캔 결과를 JSON 파일로 저장.
        
        Args:
            result: 스캔 결과 DTO.
        
        저장 실패 시에도 스캔 완료 처리는 계속 진행됩니다 (로깅만 기록).
        """
        debug_step(
            self._log_sink,
            "scan_tab_save_result_start",
            {
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
            }
        )
        
        try:
            # 프로젝트 루트의 SAVE 폴더에 절대 경로로 저장
            # scan_tab.py: src/gui/views/tabs/scan_tab.py
            # 프로젝트 루트: parent 5단계 위
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            save_dir = project_root / "SAVE"
            
            # 파일명 생성
            filename = generate_scan_json_filename(result.scan_timestamp)
            output_path = save_dir.resolve() / filename
            
            # JSON 파일로 저장
            save_scan_result_to_json(result, output_path, self._scan_folder)
            
            debug_step(
                self._log_sink,
                "scan_tab_save_result_success",
                {"output_path": str(output_path)}
            )
            
            logger.info(f"스캔 결과 JSON 저장 완료: {output_path}")
        
        except Exception as e:
            # JSON 저장 실패는 스캔 완료 처리에 영향을 주지 않음
            debug_step(
                self._log_sink,
                "scan_tab_save_result_error",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            logger.warning(f"스캔 결과 JSON 저장 실패 (스캔 완료는 정상 처리됨): {e}", exc_info=True)
