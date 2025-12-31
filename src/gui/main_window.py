"""
NovelGuard 메인 윈도우 모듈

PySide6를 사용한 기본 GUI 창을 제공합니다.
"""

from pathlib import Path
from typing import Optional
import subprocess
import sys
import os

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
)
from PySide6.QtCore import Qt, QTimer

from models.file_record import FileRecord
from scanners.file_scanner import FileScannerThread
from analyzers.duplicate_analyzer_thread import DuplicateAnalyzerThread
from analyzers.duplicate_group import DuplicateGroup
from checkers.integrity_checker_thread import IntegrityCheckerThread
from checkers.integrity_checker import IntegrityIssue
from utils.logger import get_logger
from utils.constants import (
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    LAYOUT_SPACING,
    LAYOUT_MARGINS,
    TITLE_FONT_SIZE,
    SUBTITLE_FONT_SIZE,
    BUTTON_MIN_WIDTH,
    BUTTON_MIN_HEIGHT,
    TABLE_COLUMN_COUNT,
    TABLE_MIN_HEIGHT,
)
from gui.managers.scan_result_manager import ScanResultManager
from gui.managers.settings_manager import SettingsManager
from gui.updaters.duplicate_result_updater import DuplicateResultUpdater
from gui.updaters.integrity_result_updater import IntegrityResultUpdater
from gui.workflows.file_organization_workflow import FileOrganizationWorkflow
from gui.factories.table_item_factory import TableItemFactory


class MainWindow(QMainWindow):
    """NovelGuard 메인 윈도우 클래스.
    
    텍스트 소설 파일 정리를 위한 기본 GUI 인터페이스를 제공합니다.
    
    Attributes:
        central_widget: 중앙 위젯
        folder_path: 선택된 폴더 경로
        file_table: 파일 목록 테이블 위젯
        settings: 애플리케이션 설정 저장소
    """
    
    def __init__(self) -> None:
        """메인 윈도우 초기화."""
        super().__init__()
        
        # 로거 초기화
        self._logger = get_logger("MainWindow")
        
        # 매니저 클래스 초기화
        self._settings_manager = SettingsManager()
        self._scan_result_manager = ScanResultManager()
        
        self.folder_path: Optional[Path] = None
        self.file_table: Optional[QTableWidget] = None
        self.scanner_thread: Optional[FileScannerThread] = None
        self.duplicate_analyzer_thread: Optional[DuplicateAnalyzerThread] = None
        self.integrity_checker_thread: Optional[IntegrityCheckerThread] = None
        self.duplicate_check_btn: Optional[QPushButton] = None
        self.integrity_check_btn: Optional[QPushButton] = None
        # 중복 분석 결과 저장 (메시지박스 지연 표시용)
        self._pending_duplicate_message: Optional[tuple[bool, int, int]] = None  # (has_duplicates, group_count, total_count)
        # 중복 그룹 정보 저장 (파일 정리용)
        self._duplicate_groups: list[DuplicateGroup] = []
        # 업데이터 초기화 (테이블이 생성된 후 _setup_layout에서 초기화됨)
        self._duplicate_result_updater: Optional[DuplicateResultUpdater] = None
        self._integrity_result_updater: Optional[IntegrityResultUpdater] = None
        
        self._init_ui()
        self._setup_layout()
        self._load_and_display_last_folder()
        
        # 워크플로우 초기화 (폴더 경로가 설정된 후)
        self._file_organization_workflow: Optional[FileOrganizationWorkflow] = None
        # 팩토리 초기화
        self._table_item_factory = TableItemFactory()
        
        self._logger.info("메인 윈도우 초기화 완료")
        
    def _init_ui(self) -> None:
        """UI 초기화."""
        self.setWindowTitle("NovelGuard - 텍스트 소설 파일 정리 도구")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # 중앙 위젯 생성
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
    def _setup_layout(self) -> None:
        """레이아웃 설정."""
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setSpacing(LAYOUT_SPACING)
        main_layout.setContentsMargins(*LAYOUT_MARGINS)
        
        # 제목 레이블
        title_label = QLabel("NovelGuard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title_label.font()
        font.setPointSize(TITLE_FONT_SIZE)
        font.setBold(True)
        title_label.setFont(font)
        main_layout.addWidget(title_label)
        
        # 부제목 레이블
        subtitle_label = QLabel("텍스트 소설 파일 정리 도구")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(f"color: #666; font-size: {SUBTITLE_FONT_SIZE}px;")
        main_layout.addWidget(subtitle_label)
        
        # 구분선
        main_layout.addSpacing(20)
        
        # 폴더 선택 섹션
        folder_layout = QVBoxLayout()
        folder_label = QLabel("대상 폴더:")
        folder_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        folder_layout.addWidget(folder_label)
        
        # 폴더 경로 표시 및 선택 버튼
        folder_select_layout = QHBoxLayout()
        
        self.folder_path_label = QLabel("폴더를 선택해주세요")
        self.folder_path_label.setStyleSheet(
            "padding: 8px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; color: #333;"
        )
        folder_select_layout.addWidget(self.folder_path_label, stretch=1)
        
        self.select_folder_btn = QPushButton("폴더 선택")
        self.select_folder_btn.setMinimumWidth(BUTTON_MIN_WIDTH)
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        folder_select_layout.addWidget(self.select_folder_btn)
        
        folder_layout.addLayout(folder_select_layout)
        main_layout.addLayout(folder_layout)
        
        # 파일 목록 테이블
        table_label = QLabel("파일 목록:")
        table_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        main_layout.addWidget(table_label)
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(TABLE_COLUMN_COUNT)
        self.file_table.setHorizontalHeaderLabels(["파일명", "파일 크기", "인코딩", "중복 여부", "무결성 상태"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setMinimumHeight(TABLE_MIN_HEIGHT)
        # 정렬 기능 활성화
        self.file_table.setSortingEnabled(True)
        # 더블 클릭 이벤트 연결
        self.file_table.itemDoubleClicked.connect(self._on_file_double_clicked)
        main_layout.addWidget(self.file_table)
        
        # 중복 결과 업데이터 초기화
        def show_message(has_duplicates: bool, group_count: int, total_count: int) -> None:
            """메시지박스 표시 콜백."""
            if has_duplicates:
                QMessageBox.information(
                    self,
                    "중복 검사 완료",
                    f"{group_count}개의 중복 그룹을 발견했습니다.\n"
                    f"총 {total_count}개의 중복 파일이 있습니다."
                )
            else:
                QMessageBox.information(
                    self,
                    "중복 검사 완료",
                    "중복 파일을 찾을 수 없습니다."
                )
        
        self._duplicate_result_updater = DuplicateResultUpdater(
            self.file_table,
            message_callback=show_message
        )
        
        # 무결성 결과 업데이터 초기화
        self._integrity_result_updater = IntegrityResultUpdater(self.file_table)
        
        # 액션 버튼 섹션
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.scan_btn = QPushButton("스캔 시작")
        self.scan_btn.setMinimumWidth(BUTTON_MIN_WIDTH)
        self.scan_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._on_scan_start)
        action_layout.addWidget(self.scan_btn)
        
        self.duplicate_check_btn = QPushButton("중복 검사")
        self.duplicate_check_btn.setMinimumWidth(BUTTON_MIN_WIDTH)
        self.duplicate_check_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.duplicate_check_btn.setEnabled(False)
        self.duplicate_check_btn.clicked.connect(self._on_duplicate_check)
        action_layout.addWidget(self.duplicate_check_btn)
        
        self.integrity_check_btn = QPushButton("무결성 확인")
        self.integrity_check_btn.setMinimumWidth(BUTTON_MIN_WIDTH)
        self.integrity_check_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
        self.integrity_check_btn.setEnabled(False)
        self.integrity_check_btn.clicked.connect(self._on_integrity_check)
        action_layout.addWidget(self.integrity_check_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # 상태 레이블
        self.status_label = QLabel("준비됨")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        main_layout.addWidget(self.status_label)
        
        # 레이아웃 적용
        self.central_widget.setLayout(main_layout)
    
    def _load_and_display_last_folder(self) -> None:
        """저장된 마지막 폴더를 로드하여 UI에 표시합니다.
        
        애플리케이션 시작 시 저장된 마지막 폴더 경로를 표시하고,
        유효한 경로이면 스캔 버튼을 활성화합니다.
        """
        last_folder = self._settings_manager.load_last_folder()
        if last_folder:
            try:
                folder_path = Path(last_folder)
                if folder_path.exists() and folder_path.is_dir():
                    self.folder_path = folder_path
                    self.folder_path_label.setText(str(folder_path))
                    self.folder_path_label.setToolTip(str(folder_path))
                    self.scan_btn.setEnabled(True)
                    self.status_label.setText(f"마지막 선택 폴더: {folder_path.name}")
                    self._logger.info(f"마지막 선택 폴더 로드 성공: {folder_path}")
            except Exception as e:
                # 경로 로드 오류는 로그만 기록하고 무시
                self._logger.warning(f"마지막 선택 폴더 로드 실패: {e}")
        
    def _on_select_folder(self) -> None:
        """폴더 선택 버튼 클릭 핸들러.
        
        사용자가 폴더를 선택하면 경로를 저장하고 UI를 업데이트합니다.
        저장된 마지막 폴더 경로를 기본 경로로 사용합니다.
        """
        # 저장된 마지막 폴더 경로 로드
        last_folder = self._settings_manager.load_last_folder()
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "정리할 소설 파일이 있는 폴더를 선택하세요",
            last_folder,  # 저장된 경로를 기본 경로로 사용
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            try:
                self.folder_path = Path(folder)
                self.folder_path_label.setText(str(self.folder_path))
                self.folder_path_label.setToolTip(str(self.folder_path))
                self.scan_btn.setEnabled(True)
                self.status_label.setText(f"폴더 선택됨: {self.folder_path.name}")
                
                # 선택한 폴더 경로 저장
                self._settings_manager.save_last_folder(str(self.folder_path))
                
                # 파일 정리 워크플로우 초기화
                self._init_file_organization_workflow()
                
                self._logger.info(f"폴더 선택됨: {self.folder_path}")
            except Exception as e:
                self._logger.error(f"폴더 선택 처리 중 오류: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "오류",
                    f"폴더 선택 처리 중 오류가 발생했습니다: {str(e)}"
                )
            
    def _on_scan_start(self) -> None:
        """스캔 시작 버튼 클릭 핸들러.
        
        백그라운드 스레드에서 대상 폴더 내 .txt 파일을 재귀적으로 스캔합니다.
        """
        if not self.folder_path:
            self._logger.warning("스캔 시작 시도: 폴더가 선택되지 않음")
            QMessageBox.warning(
                self,
                "경고",
                "폴더를 먼저 선택해주세요."
            )
            return
        
        # 이미 스캔 중이면 중단
        if self.scanner_thread and self.scanner_thread.isRunning():
            self._logger.info("기존 스캔 중단 요청")
            self.scanner_thread.requestInterruption()
            self.scanner_thread.wait()
        
        self._logger.info(f"파일 스캔 시작: {self.folder_path}")
        self.status_label.setText("스캔 중...")
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("스캔 중...")
        
        # 테이블 초기화
        self.file_table.setRowCount(0)
        self._scan_result_manager.clear()
        # 중복 결과 업데이터 캐시 초기화
        if self._duplicate_result_updater:
            self._duplicate_result_updater.clear_cache()
        # 메시지박스 정보 초기화
        self._pending_duplicate_message = None
        
        # 중복 검사 및 무결성 확인 버튼 비활성화
        self.duplicate_check_btn.setEnabled(False)
        self.integrity_check_btn.setEnabled(False)
        
        # 스캔 스레드 생성 및 시작
        try:
            self.scanner_thread = FileScannerThread(self.folder_path, detect_encoding=False)
            self.scanner_thread.files_found_batch.connect(self._on_files_found_batch)
            self.scanner_thread.scan_finished.connect(self._on_scan_finished)
            self.scanner_thread.scan_error.connect(self._on_scan_error)
            self.scanner_thread.start()
        except Exception as e:
            self._logger.error(f"스캔 스레드 생성 실패: {e}", exc_info=True)
            self.status_label.setText("스캔 시작 실패")
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("스캔 시작")
            QMessageBox.critical(
                self,
                "오류",
                f"스캔을 시작할 수 없습니다: {str(e)}"
            )
    
    def _on_files_found_batch(self, file_records: list[FileRecord]) -> None:
        """파일 발견 시그널 핸들러 (배치).
        
        여러 파일을 한 번에 처리하여 UI 업데이트 오버헤드를 줄입니다.
        
        Args:
            file_records: 발견된 파일 정보 FileRecord 리스트
        """
        if not file_records:
            return
        
        # 스캔 결과 매니저에 추가
        current_files = self._scan_result_manager.get_scanned_files()
        current_files.extend(file_records)
        self._scan_result_manager.set_scan_results(current_files, self.folder_path)
        
        # 배치로 추가하여 UI 업데이트 최적화
        start_row = self.file_table.rowCount()
        self.file_table.setRowCount(start_row + len(file_records))
        
        for idx, file_record in enumerate(file_records):
            row = start_row + idx
            
            # 테이블 아이템 생성 (팩토리 사용)
            items = self._table_item_factory.create_row_items(file_record)
            for col, item in enumerate(items):
                self.file_table.setItem(row, col, item)
        
            # 상태 업데이트 (배치마다 한 번만)
        scanned_count = len(self._scan_result_manager.get_scanned_files())
        self.status_label.setText(f"스캔 중... ({scanned_count}개 파일 발견)")
        
    def _on_scan_finished(self, total_count: int) -> None:
        """스캔 완료 시그널 핸들러.
        
        Args:
            total_count: 발견된 파일 총 개수
        """
        self._logger.info(f"파일 스캔 완료: {total_count}개 파일 발견")
        
        if total_count == 0:
            self.status_label.setText("스캔 완료: .txt 파일을 찾을 수 없습니다.")
            self._logger.warning(f"스캔 완료: 파일 없음 - {self.folder_path}")
            QMessageBox.information(
                self,
                "알림",
                "선택한 폴더에서 .txt 파일을 찾을 수 없습니다."
            )
        else:
            # 테이블 정렬 (파일명 기준)
            # O(n log n)이지만 스캔 완료 후 한 번만 수행
            # 대안: 스캔 중 삽입 정렬 사용 가능하나, 사용자 경험상 완료 후 정렬이 더 나음
            # 정렬 기능이 활성화되어 있으면 사용자가 헤더를 클릭하여 정렬할 수 있으므로
            # 초기 정렬만 수행 (선택적)
            # self.file_table.sortItems(0, Qt.SortOrder.AscendingOrder)
            
            # 스캔 결과 매니저에 설정
            self._scan_result_manager.set_scan_results(
                self._scan_result_manager.get_scanned_files(),
                self.folder_path
            )
            
            # JSON 파일로 저장
            saved_filename = None
            try:
                saved_filename = self._scan_result_manager.save_to_json()
            except Exception as e:
                self._logger.error(f"스캔 결과 JSON 저장 실패: {e}", exc_info=True)
                # 저장 실패해도 스캔은 정상 완료로 처리
            
            # 상태 레이블 업데이트
            if saved_filename:
                self.status_label.setText(f"스캔 완료: {total_count}개 파일 발견 (저장: {saved_filename})")
            else:
                self.status_label.setText(f"스캔 완료: {total_count}개 파일 발견")
            
            # 중복 검사 및 무결성 확인 버튼 활성화 (파일이 1개 이상 있을 때만)
            self.duplicate_check_btn.setEnabled(True)
            self.integrity_check_btn.setEnabled(True)
        
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("스캔 시작")
        
    def _on_scan_error(self, error_message: str) -> None:
        """스캔 오류 시그널 핸들러.
        
        Args:
            error_message: 오류 메시지
        """
        self._logger.error(f"파일 스캔 오류: {error_message}")
        self.status_label.setText("스캔 오류 발생")
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("스캔 시작")
        
        QMessageBox.warning(
            self,
            "스캔 오류",
            error_message
        )
    
    def _on_duplicate_check(self) -> None:
        """중복 검사 버튼 클릭 핸들러.
        
        백그라운드 스레드에서 중복 파일 분석을 수행합니다.
        """
        scanned_files = self._scan_result_manager.get_scanned_files()
        if not scanned_files:
            QMessageBox.warning(
                self,
                "경고",
                "검사할 파일이 없습니다. 먼저 스캔을 진행해주세요."
            )
            return
        
        # 이미 분석 중이면 중단
        if self.duplicate_analyzer_thread and self.duplicate_analyzer_thread.isRunning():
            self._logger.info("기존 중복 분석 중단 요청")
            self.duplicate_analyzer_thread.requestInterruption()
            self.duplicate_analyzer_thread.wait()
        
        self._logger.info(f"중복 검사 시작: {len(scanned_files)}개 파일")
        self.status_label.setText("중복 검사 중...")
        self.duplicate_check_btn.setEnabled(False)
        self.duplicate_check_btn.setText("검사 중...")
        
        # 중복 분석 스레드 생성 및 시작
        try:
            self.duplicate_analyzer_thread = DuplicateAnalyzerThread(scanned_files)
            # analysis_finished 시그널은 제거 (analysis_finished_with_groups만 사용)
            self.duplicate_analyzer_thread.analysis_finished_with_groups.connect(self._on_duplicate_analysis_finished_with_groups)
            self.duplicate_analyzer_thread.analysis_error.connect(self._on_duplicate_analysis_error)
            self.duplicate_analyzer_thread.progress_updated.connect(self._on_duplicate_progress_updated)
            self.duplicate_analyzer_thread.start()
        except Exception as e:
            self._logger.error(f"중복 분석 스레드 생성 실패: {e}", exc_info=True)
            self.status_label.setText("중복 검사 시작 실패")
            self.duplicate_check_btn.setEnabled(True)
            self.duplicate_check_btn.setText("중복 검사")
            QMessageBox.critical(
                self,
                "오류",
                f"중복 검사를 시작할 수 없습니다: {str(e)}"
            )
    
    def _on_duplicate_analysis_finished(self, duplicate_groups: list[list[FileRecord]]) -> None:
        """중복 분석 완료 시그널 핸들러 (기존 호환성).
        
        Args:
            duplicate_groups: 중복 그룹 리스트
        """
        self._logger.info(f"중복 분석 완료: {len(duplicate_groups)}개 그룹 발견")
        
        # 메시지박스 정보 설정
        total_duplicates = sum(len(group) for group in duplicate_groups)
        if duplicate_groups:
            self._pending_duplicate_message = (True, len(duplicate_groups), total_duplicates)
        else:
            self._pending_duplicate_message = (False, 0, 0)
        
        # 결과 업데이트를 이벤트 루프에 예약 (비동기 처리로 UI 반응성 유지)
        # QTimer.singleShot(0, ...)를 사용하여 현재 이벤트 루프 사이클이 끝난 후 실행
        QTimer.singleShot(0, lambda: self._update_duplicate_results(duplicate_groups))
    
    def _on_duplicate_analysis_finished_with_groups(self, duplicate_groups: list[DuplicateGroup]) -> None:
        """중복 분석 완료 시그널 핸들러 (DuplicateGroup 정보 포함).
        
        Args:
            duplicate_groups: 중복 그룹 리스트 (keep_file 정보 포함)
        """
        self._logger.info(f"중복 분석 완료 (그룹 정보 포함): {len(duplicate_groups)}개 그룹 발견")
        
        # 중복 그룹 정보 저장
        self._duplicate_groups = duplicate_groups
        
        # 결과 요약 표시
        total_duplicates = sum(len(group.members) for group in duplicate_groups)
        if duplicate_groups:
            self.status_label.setText(
                f"중복 검사 완료: {len(duplicate_groups)}개 그룹, "
                f"{total_duplicates}개 중복 파일 발견"
            )
            # 메시지박스는 업데이트 완료 후 표시 (지연) - 프리징 체감 최소화
            self._pending_duplicate_message = (True, len(duplicate_groups), total_duplicates)
            
            # 버튼 텍스트 변경 및 핸들러 전환
            self.duplicate_check_btn.setText("파일 정리 실행")
            self.duplicate_check_btn.clicked.disconnect()
            self.duplicate_check_btn.clicked.connect(self._on_organize_files)
        else:
            self.status_label.setText("중복 검사 완료: 중복 파일 없음")
            # 메시지박스는 업데이트 완료 후 표시 (지연) - 프리징 체감 최소화
            self._pending_duplicate_message = (False, 0, 0)
            # 중복이 없으면 버튼 상태 유지
            self.duplicate_check_btn.setText("중복 검사")
        
        self.duplicate_check_btn.setEnabled(True)
        
        # DuplicateGroup을 직접 전달하여 테이블 업데이트 (keep_file 포함, 파일 정리와 일치)
        QTimer.singleShot(0, lambda: self._update_duplicate_results_with_groups(duplicate_groups))
    
    def _on_duplicate_analysis_error(self, error_message: str) -> None:
        """중복 분석 오류 시그널 핸들러.
        
        Args:
            error_message: 오류 메시지
        """
        self._logger.error(f"중복 분석 오류: {error_message}")
        self.status_label.setText("중복 검사 오류 발생")
        self.duplicate_check_btn.setEnabled(True)
        self.duplicate_check_btn.setText("중복 검사")
        
        QMessageBox.warning(
            self,
            "중복 검사 오류",
            error_message
        )
    
    def _on_duplicate_progress_updated(self, message: str) -> None:
        """중복 분석 진행 상황 업데이트 시그널 핸들러.
        
        Args:
            message: 진행 상황 메시지
        """
        self.status_label.setText(message)
    
    def _on_integrity_check(self) -> None:
        """무결성 확인 버튼 클릭 핸들러.
        
        IntegrityCheckerThread를 사용하여 백그라운드에서 파일 무결성을 검사합니다.
        """
        scanned_files = self._scan_result_manager.get_scanned_files()
        if not scanned_files:
            QMessageBox.warning(
                self,
                "경고",
                "검사할 파일이 없습니다. 먼저 스캔을 진행해주세요."
            )
            return
        
        # 이미 검사 중이면 중단
        if self.integrity_checker_thread and self.integrity_checker_thread.isRunning():
            self._logger.info("기존 무결성 검사 중단 요청")
            self.integrity_checker_thread.requestInterruption()
            self.integrity_checker_thread.wait()
        
        self._logger.info(f"무결성 확인 시작: {len(scanned_files)}개 파일")
        self.status_label.setText("무결성 확인 중...")
        self.integrity_check_btn.setEnabled(False)
        self.integrity_check_btn.setText("확인 중...")
        
        # 무결성 검사 스레드 생성 및 시작
        try:
            self.integrity_checker_thread = IntegrityCheckerThread(scanned_files)
            self.integrity_checker_thread.check_finished.connect(self._on_integrity_check_finished)
            self.integrity_checker_thread.check_error.connect(self._on_integrity_check_error)
            self.integrity_checker_thread.progress_updated.connect(self._on_integrity_progress_updated)
            self.integrity_checker_thread.start()
        except Exception as e:
            self._logger.error(f"무결성 검사 스레드 생성 실패: {e}", exc_info=True)
            self.status_label.setText("무결성 검사 시작 실패")
            self.integrity_check_btn.setEnabled(True)
            self.integrity_check_btn.setText("무결성 확인")
            QMessageBox.warning(
                self,
                "오류",
                f"무결성 검사 시작 실패: {str(e)}"
            )
    
    def _on_integrity_check_finished(self, issues: list[IntegrityIssue]) -> None:
        """무결성 검사 완료 핸들러.
        
        Args:
            issues: 무결성 문제 리스트
        """
        self._logger.info(f"무결성 검사 완료: {len(issues)}개 문제 발견")
        
        # 결과 업데이트
        self._update_integrity_results(issues)
        
        # 결과 요약 메시지
        error_count = sum(1 for issue in issues if issue.severity == "ERROR")
        warn_count = sum(1 for issue in issues if issue.severity == "WARN")
        info_count = sum(1 for issue in issues if issue.severity == "INFO")
        
        if error_count > 0 or warn_count > 0:
            message = f"무결성 검사 완료:\n"
            if error_count > 0:
                message += f"- 오류: {error_count}개\n"
            if warn_count > 0:
                message += f"- 경고: {warn_count}개\n"
            if info_count > 0:
                message += f"- 정보: {info_count}개"
            QMessageBox.information(self, "무결성 검사 완료", message)
        else:
            scanned_files = self._scan_result_manager.get_scanned_files()
            QMessageBox.information(
                self,
                "무결성 검사 완료",
                f"모든 파일이 정상입니다. ({len(scanned_files)}개 파일 검사)"
            )
        
        # 버튼 상태 복원
        self.integrity_check_btn.setEnabled(True)
        self.integrity_check_btn.setText("무결성 확인")
        self.status_label.setText("무결성 확인 완료")
    
    def _on_integrity_check_error(self, error_message: str) -> None:
        """무결성 검사 오류 핸들러.
        
        Args:
            error_message: 오류 메시지
        """
        self._logger.error(f"무결성 검사 오류: {error_message}")
        QMessageBox.warning(
            self,
            "오류",
            f"무결성 확인 중 오류가 발생했습니다:\n{error_message}"
        )
        
        # 버튼 상태 복원
        self.integrity_check_btn.setEnabled(True)
        self.integrity_check_btn.setText("무결성 확인")
        self.status_label.setText("무결성 확인 실패")
    
    def _on_integrity_progress_updated(self, message: str) -> None:
        """무결성 검사 진행 상황 업데이트 핸들러.
        
        Args:
            message: 진행 상황 메시지
        """
        self.status_label.setText(message)
    
    def _update_duplicate_results(self, duplicate_groups: list[list[FileRecord]]) -> None:
        """중복 검사 결과를 테이블에 업데이트 (기존 호환성).
        
        중복 그룹을 기반으로 테이블의 "중복 여부" 컬럼을 업데이트합니다.
        DuplicateResultUpdater를 사용하여 효율적으로 업데이트합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트. 각 그룹은 FileRecord 리스트.
        """
        self._logger.debug(f"_update_duplicate_results 호출: {len(duplicate_groups)}개 그룹")
        
        if not self._duplicate_result_updater:
            self._logger.warning("DuplicateResultUpdater가 초기화되지 않았습니다.")
            return
        
        if not self.file_table:
            self._logger.warning("file_table이 초기화되지 않았습니다.")
            return
        
        self._logger.debug(f"테이블 행 수: {self.file_table.rowCount()}")
        self._duplicate_result_updater.update_results(
            duplicate_groups,
            message_info=self._pending_duplicate_message
        )
    
    def _update_duplicate_results_with_groups(self, duplicate_groups: list[DuplicateGroup]) -> None:
        """중복 검사 결과를 테이블에 업데이트 (DuplicateGroup 정보 포함).
        
        중복 그룹을 기반으로 테이블의 "중복 여부" 컬럼을 업데이트합니다.
        keep_file은 "보관"으로, 나머지는 "중복"으로 표시하여 파일 정리와 일치시킵니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트 (keep_file 정보 포함)
        """
        self._logger.debug(f"_update_duplicate_results_with_groups 호출: {len(duplicate_groups)}개 그룹")
        
        if not self._duplicate_result_updater:
            self._logger.warning("DuplicateResultUpdater가 초기화되지 않았습니다.")
            return
        
        if not self.file_table:
            self._logger.warning("file_table이 초기화되지 않았습니다.")
            return
        
        self._logger.debug(f"테이블 행 수: {self.file_table.rowCount()}")
        self._duplicate_result_updater.update_results_with_groups(
            duplicate_groups,
            message_info=self._pending_duplicate_message
        )
    
    
    def _update_integrity_results(self, issues: list[IntegrityIssue]) -> None:
        """무결성 검사 결과를 테이블에 업데이트.
        
        IntegrityResultUpdater를 사용하여 배치 업데이트를 수행합니다.
        
        Args:
            issues: 무결성 문제 리스트 (IntegrityIssue 객체들)
        """
        if not self._integrity_result_updater:
            self._logger.warning("IntegrityResultUpdater가 초기화되지 않았습니다.")
            return
        
        if not self.file_table:
            self._logger.warning("file_table이 초기화되지 않았습니다.")
            return
        
        self._integrity_result_updater.update_results(issues)
    
    def _on_file_double_clicked(self, item: QTableWidgetItem) -> None:
        """파일 더블 클릭 핸들러.
        
        테이블의 파일을 더블 클릭하면 시스템 기본 프로그램으로 엽니다.
        
        Args:
            item: 더블 클릭된 테이블 아이템
        """
        if not self.file_table:
            return
        
        # 클릭된 행 가져오기
        row = item.row()
        name_item = self.file_table.item(row, 0)
        if name_item is None:
            return
        
        # UserRole에서 파일 경로 가져오기
        file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
        if not file_path_str:
            return
        
        file_path = Path(file_path_str)
        
        # 파일 존재 여부 확인
        if not file_path.exists():
            QMessageBox.warning(
                self,
                "파일 없음",
                f"파일이 존재하지 않습니다:\n{file_path}"
            )
            return
        
        # 파일이 디렉토리인 경우
        if file_path.is_dir():
            QMessageBox.information(
                self,
                "알림",
                "디렉토리는 열 수 없습니다."
            )
            return
        
        # 시스템 기본 프로그램으로 파일 열기
        try:
            if sys.platform == "win32":
                # Windows: os.startfile 사용
                os.startfile(file_path)
            elif sys.platform == "darwin":
                # macOS: open 명령어 사용
                subprocess.Popen(["open", str(file_path)])
            else:
                # Linux: xdg-open 사용
                subprocess.Popen(["xdg-open", str(file_path)])
            
            self._logger.info(f"파일 열기: {file_path}")
            
        except Exception as e:
            self._logger.error(f"파일 열기 실패: {file_path} - {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "파일 열기 실패",
                f"파일을 열 수 없습니다:\n{file_path}\n\n오류: {str(e)}"
            )
    
    def _init_file_organization_workflow(self) -> None:
        """파일 정리 워크플로우를 초기화합니다."""
        if not self.folder_path:
            return
        
        def status_callback(message: str) -> None:
            """상태 업데이트 콜백."""
            self.status_label.setText(message)
        
        def button_callback(enabled: bool, text: str) -> None:
            """버튼 상태 업데이트 콜백."""
            self.duplicate_check_btn.setEnabled(enabled)
            self.duplicate_check_btn.setText(text)
        
        self._file_organization_workflow = FileOrganizationWorkflow(
            root_folder=self.folder_path,
            scan_result_manager=self._scan_result_manager,
            table=self.file_table,
            status_callback=status_callback,
            button_callback=button_callback
        )
    
    def _on_organize_files(self) -> None:
        """파일 정리 실행 버튼 클릭 핸들러.
        
        중복 파일을 old_versions 폴더로 이동시킵니다.
        FileOrganizationWorkflow를 사용하여 워크플로우를 실행합니다.
        """
        if not self._duplicate_groups:
            QMessageBox.warning(
                self,
                "경고",
                "정리할 중복 그룹이 없습니다. 먼저 중복 검사를 진행해주세요."
            )
            return
        
        if not self.folder_path:
            QMessageBox.warning(
                self,
                "경고",
                "폴더 경로가 설정되지 않았습니다."
            )
            return
        
        if not self._file_organization_workflow:
            self._init_file_organization_workflow()
        
        if not self._file_organization_workflow:
            QMessageBox.warning(
                self,
                "경고",
                "파일 정리 워크플로우를 초기화할 수 없습니다."
            )
            return
        
        self._logger.info(f"파일 정리 시작: {len(self._duplicate_groups)}개 그룹")
        
        # 워크플로우 실행
        success = self._file_organization_workflow.execute(
            self._duplicate_groups,
            parent_widget=self
        )
        
        if success:
            # 중복 그룹 정보 초기화 (이미 이동 완료)
            self._duplicate_groups = []
            
            # 버튼 상태 복원
            self.duplicate_check_btn.setText("중복 검사")
            self.duplicate_check_btn.clicked.disconnect()
            self.duplicate_check_btn.clicked.connect(self._on_duplicate_check)

