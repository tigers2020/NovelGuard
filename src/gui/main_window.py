"""
NovelGuard 메인 윈도우 모듈

PySide6를 사용한 기본 GUI 창을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Any
import logging
import json
from datetime import datetime

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
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QSettings, QTimer, QSignalBlocker

from models.file_record import FileRecord
from scanners.file_scanner import FileScannerThread
from analyzers.duplicate_analyzer_thread import DuplicateAnalyzerThread
from analyzers.duplicate_group import DuplicateGroup
from utils.formatters import format_file_size
from utils.logger import get_logger
from utils.file_organizer import FileOrganizer
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
    DUPLICATE_UPDATE_BATCH_SIZE,
    UI_UPDATE_DELAY_MS,
    JSON_INDENT,
    DEFAULT_ENCODING,
)


class MainWindow(QMainWindow):
    """NovelGuard 메인 윈도우 클래스.
    
    텍스트 소설 파일 정리를 위한 기본 GUI 인터페이스를 제공합니다.
    
    Attributes:
        central_widget: 중앙 위젯
        folder_path: 선택된 폴더 경로
        file_table: 파일 목록 테이블 위젯
        settings: 애플리케이션 설정 저장소
    """
    
    # 설정 키 상수
    SETTING_LAST_FOLDER = "last_selected_folder"
    
    def __init__(self) -> None:
        """메인 윈도우 초기화."""
        super().__init__()
        
        # 로거 초기화
        self._logger = get_logger("MainWindow")
        
        # QSettings 초기화 (애플리케이션 이름과 조직명 설정)
        self.settings = QSettings("NovelGuard", "NovelGuard")
        
        self.folder_path: Optional[Path] = None
        self.file_table: Optional[QTableWidget] = None
        self.scanner_thread: Optional[FileScannerThread] = None
        self.duplicate_analyzer_thread: Optional[DuplicateAnalyzerThread] = None
        self.scanned_files: list[FileRecord] = []
        self.duplicate_check_btn: Optional[QPushButton] = None
        self.integrity_check_btn: Optional[QPushButton] = None
        self._duplicate_update_timer: Optional[QTimer] = None
        self._pending_duplicate_updates: list[tuple[int, str, bool, Optional[QTableWidgetItem]]] = []  # (row, text, is_duplicate, item)
        # 중복 상태 캐시: path -> (is_duplicate, group_num)
        self._dup_state_by_path: dict[str, tuple[bool, int]] = {}
        # 중복 분석 결과 저장 (메시지박스 지연 표시용)
        self._pending_duplicate_message: Optional[tuple[bool, int, int]] = None  # (has_duplicates, group_count, total_count)
        # 중복 그룹 정보 저장 (파일 정리용)
        self._duplicate_groups: list[DuplicateGroup] = []
        
        self._init_ui()
        self._setup_layout()
        self._load_and_display_last_folder()
        
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
        main_layout.addWidget(self.file_table)
        
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
        last_folder = self._load_last_folder()
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
        last_folder = self._load_last_folder()
        
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
                self._save_last_folder(str(self.folder_path))
                self._logger.info(f"폴더 선택됨: {self.folder_path}")
            except Exception as e:
                self._logger.error(f"폴더 선택 처리 중 오류: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "오류",
                    f"폴더 선택 처리 중 오류가 발생했습니다: {str(e)}"
                )
    
    def _load_last_folder(self) -> str:
        """저장된 마지막 폴더 경로를 로드합니다.
        
        Returns:
            저장된 폴더 경로 문자열. 경로가 없거나 유효하지 않으면 빈 문자열.
        """
        try:
            last_folder = self.settings.value(self.SETTING_LAST_FOLDER, "")
            if not last_folder:
                return ""
            
            # 경로 유효성 검사
            folder_path = Path(last_folder)
            if folder_path.exists() and folder_path.is_dir():
                return str(folder_path)
            else:
                # 유효하지 않은 경로는 설정에서 제거
                self.settings.remove(self.SETTING_LAST_FOLDER)
                return ""
        except Exception:
            # 설정 읽기 오류 시 빈 문자열 반환
            return ""
    
    def _save_last_folder(self, folder_path: str) -> None:
        """마지막 선택 폴더 경로를 저장합니다.
        
        Args:
            folder_path: 저장할 폴더 경로 문자열
        """
        try:
            self.settings.setValue(self.SETTING_LAST_FOLDER, folder_path)
            self.settings.sync()  # 설정 즉시 저장
            self._logger.debug(f"마지막 폴더 경로 저장: {folder_path}")
        except Exception as e:
            # 설정 저장 오류는 로그만 기록하고 무시 (기능 동작에는 영향 없음)
            self._logger.warning(f"마지막 폴더 경로 저장 실패: {e}")
            
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
        self.scanned_files.clear()
        # 중복 상태 캐시 초기화
        self._dup_state_by_path.clear()
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
        
        # 배치로 추가하여 UI 업데이트 최적화
        start_row = self.file_table.rowCount()
        self.file_table.setRowCount(start_row + len(file_records))
        
        for idx, file_record in enumerate(file_records):
            self.scanned_files.append(file_record)
            row = start_row + idx
            
            # 파일명 (path를 userData로 저장하여 정렬 후에도 매칭 가능)
            name_item = QTableWidgetItem(file_record.name)
            name_item.setToolTip(str(file_record.path))
            name_item.setData(Qt.ItemDataRole.UserRole, str(file_record.path))  # path 저장
            self.file_table.setItem(row, 0, name_item)
            
            # 파일 크기 (포맷팅)
            size_str = format_file_size(file_record.size)
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row, 1, size_item)
            
            # 인코딩
            encoding_item = QTableWidgetItem(file_record.encoding)
            self.file_table.setItem(row, 2, encoding_item)
            
            # 중복 여부 (초기값: "-")
            duplicate_item = QTableWidgetItem("-")
            self.file_table.setItem(row, 3, duplicate_item)
            
            # 무결성 상태 (초기값: "-")
            integrity_item = QTableWidgetItem("-")
            self.file_table.setItem(row, 4, integrity_item)
        
        # 상태 업데이트 (배치마다 한 번만)
        self.status_label.setText(f"스캔 중... ({len(self.scanned_files)}개 파일 발견)")
        
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
            self.file_table.sortItems(0, Qt.SortOrder.AscendingOrder)
            
            # JSON 파일로 저장
            saved_filename = None
            try:
                saved_filename = self._save_scan_results_to_json()
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
        if not self.scanned_files:
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
        
        self._logger.info(f"중복 검사 시작: {len(self.scanned_files)}개 파일")
        self.status_label.setText("중복 검사 중...")
        self.duplicate_check_btn.setEnabled(False)
        self.duplicate_check_btn.setText("검사 중...")
        
        # 중복 분석 스레드 생성 및 시작
        try:
            self.duplicate_analyzer_thread = DuplicateAnalyzerThread(self.scanned_files)
            self.duplicate_analyzer_thread.analysis_finished.connect(self._on_duplicate_analysis_finished)
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
        
        스켈레톤 구현입니다. 이후 단계에서 실제 무결성 검사 로직이 추가됩니다.
        """
        if not self.scanned_files:
            QMessageBox.warning(
                self,
                "경고",
                "검사할 파일이 없습니다. 먼저 스캔을 진행해주세요."
            )
            return
        
        self._logger.info("무결성 확인 시작 (스켈레톤)")
        self.status_label.setText("무결성 확인 중...")
        self.integrity_check_btn.setEnabled(False)
        self.integrity_check_btn.setText("확인 중...")
        
        try:
            # TODO: 실제 무결성 검사 로직 구현
            # from checkers.integrity_checker import IntegrityChecker
            # checker = IntegrityChecker()
            # issues = checker.check(self.scanned_files)
            # self._update_integrity_results(issues)
            
            # 현재는 스켈레톤 구현
            QMessageBox.information(
                self,
                "알림",
                "무결성 확인 기능은 아직 구현되지 않았습니다."
            )
            
        except Exception as e:
            self._logger.error(f"무결성 확인 오류: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "오류",
                f"무결성 확인 중 오류가 발생했습니다: {str(e)}"
            )
        finally:
            self.integrity_check_btn.setEnabled(True)
            self.integrity_check_btn.setText("무결성 확인")
            self.status_label.setText("무결성 확인 완료")
    
    def _update_duplicate_results(self, duplicate_groups: list[list[FileRecord]]) -> None:
        """중복 검사 결과를 테이블에 업데이트.
        
        중복 그룹을 기반으로 테이블의 "중복 여부" 컬럼을 업데이트합니다.
        테이블 정렬 후에도 올바르게 작동하도록 path 기반으로 매칭합니다.
        대량 업데이트 시 UI 반응성을 위해 QTimer로 점진적 업데이트를 수행합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트. 각 그룹은 FileRecord 리스트.
        """
        import time
        start_time = time.time()
        
        self._logger.debug(f"중복 검사 결과 업데이트: {len(duplicate_groups)}개 그룹")
        
        # 기존 타이머가 있으면 중지
        if self._duplicate_update_timer:
            self._duplicate_update_timer.stop()
            self._duplicate_update_timer.deleteLater()
        
        # 파일 경로 → 그룹 번호 매핑 생성 (path 기반 비교로 안전성 확보)
        path_to_group: dict[str, int] = {}
        for group_idx, group in enumerate(duplicate_groups, start=1):
            for file_record in group:
                path_to_group[str(file_record.path)] = group_idx
        
        # 테이블 아이템을 미리 캐싱 (성능 향상)
        # 한 번만 순회하여 모든 아이템을 가져옴
        row_count = self.file_table.rowCount()
        cached_items: list[tuple[Optional[QTableWidgetItem], Optional[QTableWidgetItem]]] = []
        for row in range(row_count):
            name_item = self.file_table.item(row, 0)
            duplicate_item = self.file_table.item(row, 3)
            cached_items.append((name_item, duplicate_item))
        
        # 업데이트할 항목 리스트 생성 (diff 방식: 변경된 행만 업데이트)
        # path 기반 캐시를 사용하여 이전 상태와 비교
        self._pending_duplicate_updates = []
        changed_count = 0
        skipped_count = 0
        
        for row in range(row_count):
            name_item, duplicate_item = cached_items[row]
            if name_item is None:
                continue
            
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                continue
            
            # 새로운 상태 계산
            new_is_dup = file_path_str in path_to_group
            new_group = path_to_group.get(file_path_str, 0)
            
            # 이전 상태와 비교 (캐시 사용)
            old_state = self._dup_state_by_path.get(file_path_str, (None, None))
            old_is_dup, old_group = old_state
            
            # 상태가 동일하면 스킵 (diff 적용)
            if old_state == (new_is_dup, new_group):
                skipped_count += 1
                continue
            
            # 상태가 변경되었으므로 캐시 업데이트 및 업데이트 리스트에 추가
            self._dup_state_by_path[file_path_str] = (new_is_dup, new_group)
            changed_count += 1
            
            if new_is_dup:
                new_text = f"중복 (그룹 {new_group})"
            else:
                # 정상은 "-"로 표시 (초기값과 동일, 업데이트 최소화)
                new_text = "-"
            
            self._pending_duplicate_updates.append((row, new_text, new_is_dup, duplicate_item))
        
        self._logger.debug(
            f"중복 상태 diff: {changed_count}개 변경, {skipped_count}개 스킵 "
            f"(총 {row_count}개 중)"
        )
        
        # QTimer로 점진적 업데이트 (배치 크기: DUPLICATE_UPDATE_BATCH_SIZE개씩, UI 반응성 향상)
        # 배치 크기를 줄여서 각 배치당 소요 시간을 줄이고 UI 프리징 최소화
        self._duplicate_update_index = 0
        batch_size = DUPLICATE_UPDATE_BATCH_SIZE
        
        def update_batch() -> None:
            """배치 단위로 테이블 업데이트."""
            batch_start = time.time()
            
            end_idx = min(self._duplicate_update_index + batch_size, len(self._pending_duplicate_updates))
            
            # UI 업데이트 완전 차단 (성능 최적화)
            # 정렬, 시그널, 리사이즈, 페인팅 모두 비활성화
            was_sorting_enabled = self.file_table.isSortingEnabled()
            self.file_table.setSortingEnabled(False)
            
            # QSignalBlocker를 사용하여 시그널 차단 (RAII 패턴)
            signal_blocker = QSignalBlocker(self.file_table)
            self.file_table.setUpdatesEnabled(False)
            self.file_table.viewport().setUpdatesEnabled(False)
            
            try:
                for i in range(self._duplicate_update_index, end_idx):
                    row, text, is_duplicate, duplicate_item = self._pending_duplicate_updates[i]
                    
                    # 중복 여부 컬럼 (인덱스 3) - 캐시된 아이템 사용
                    if duplicate_item is None:
                        duplicate_item = QTableWidgetItem()
                        self.file_table.setItem(row, 3, duplicate_item)
                        # 캐시 업데이트
                        self._pending_duplicate_updates[i] = (row, text, is_duplicate, duplicate_item)
                    
                    # 텍스트 업데이트 (변경된 경우만)
                    current_text = duplicate_item.text()
                    if current_text != text:
                        duplicate_item.setText(text)
                    
                    # 색상 업데이트 (setData 사용 + 변경된 경우만)
                    current_color = duplicate_item.data(Qt.ItemDataRole.ForegroundRole)
                    new_color = Qt.GlobalColor.red if is_duplicate else Qt.GlobalColor.black
                    
                    # 색상이 변경된 경우만 업데이트
                    if current_color != new_color:
                        duplicate_item.setData(Qt.ItemDataRole.ForegroundRole, new_color)
            finally:
                # QSignalBlocker는 자동으로 해제됨 (블록 종료 시)
                # UI 업데이트 재개 (원래 상태로 복원)
                self.file_table.viewport().setUpdatesEnabled(True)
                self.file_table.setUpdatesEnabled(True)
                if was_sorting_enabled:
                    self.file_table.setSortingEnabled(True)
                # 마지막에 한 번만 viewport 업데이트
                self.file_table.viewport().update()
            
            batch_elapsed = (time.time() - batch_start) * 1000
            self._duplicate_update_index = end_idx
            
            # 더 업데이트할 항목이 있으면 다음 배치 예약
            if self._duplicate_update_index < len(self._pending_duplicate_updates):
                # UI_UPDATE_DELAY_MS 후 다음 배치 (이벤트 루프에 여유 제공)
                QTimer.singleShot(UI_UPDATE_DELAY_MS, update_batch)
            else:
                # 모든 업데이트 완료
                elapsed = (time.time() - start_time) * 1000
                self._pending_duplicate_updates = []
                
                # 메시지박스 지연 표시 (업데이트 완료 후) - 프리징 체감 최소화
                if self._pending_duplicate_message is not None:
                    has_duplicates, group_count, total_count = self._pending_duplicate_message
                    self._pending_duplicate_message = None
                    
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
        
        # 첫 배치 시작 (즉시 실행)
        update_batch()
    
    def _save_scan_results_to_json(self) -> Optional[str]:
        """스캔 결과를 JSON 파일로 저장합니다.
        
        SAVE 폴더에 타임스탬프가 포함된 파일명으로 저장합니다.
        FileRecord는 Pydantic 모델이므로 model_dump()를 사용하여 딕셔너리로 변환합니다.
        
        Returns:
            저장된 JSON 파일명. 저장 실패 시 None.
        """
        if not self.scanned_files:
            self._logger.warning("저장할 스캔 결과가 없습니다.")
            return None
        
        try:
            # SAVE 폴더 생성 (프로젝트 루트 기준)
            project_root = Path(__file__).parent.parent.parent
            save_dir = project_root / "SAVE"
            save_dir.mkdir(exist_ok=True)
            
            # 타임스탬프 포함 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"scan_results_{timestamp}.json"
            json_path = save_dir / json_filename
            
            # FileRecord 리스트를 딕셔너리 리스트로 변환
            # Path 객체는 문자열로 변환하고, episode_range 튜플은 리스트로 변환
            records_data = []
            for record in self.scanned_files:
                record_dict = record.model_dump()
                # Path 객체를 문자열로 변환
                record_dict["path"] = str(record_dict["path"])
                # episode_range 튜플을 리스트로 변환 (JSON 호환)
                if record_dict.get("episode_range") is not None:
                    record_dict["episode_range"] = list(record_dict["episode_range"])
                records_data.append(record_dict)
            
            # 메타데이터 포함 JSON 구조
            json_data = {
                "scan_info": {
                    "scan_time": datetime.now().isoformat(),
                    "folder_path": str(self.folder_path) if self.folder_path else None,
                    "total_files": len(self.scanned_files),
                },
                "files": records_data
            }
            
            # JSON 파일로 저장 (UTF-8 인코딩, 들여쓰기 포함)
            with open(json_path, "w", encoding=DEFAULT_ENCODING) as f:
                json.dump(json_data, f, ensure_ascii=False, indent=JSON_INDENT)
            
            self._logger.info(f"스캔 결과 JSON 저장 완료: {json_path}")
            return json_filename
            
        except Exception as e:
            self._logger.error(f"스캔 결과 JSON 저장 중 오류: {e}", exc_info=True)
            return None
    
    def _update_integrity_results(self, issues: list) -> None:
        """무결성 검사 결과를 테이블에 업데이트.
        
        스켈레톤 구현입니다. 이후 단계에서 실제 결과 업데이트 로직이 추가됩니다.
        
        Args:
            issues: 무결성 문제 리스트 (IntegrityIssue 객체들).
        """
        # TODO: 무결성 문제를 기반으로 테이블의 "무결성 상태" 컬럼 업데이트
        # 예: "정상", "경고: 빈 파일", "오류: 인코딩 문제" 등으로 표시
        self._logger.debug(f"무결성 검사 결과 업데이트: {len(issues)}개 문제")
        pass
    
    def _on_organize_files(self) -> None:
        """파일 정리 실행 버튼 클릭 핸들러.
        
        중복 파일을 old_versions 폴더로 이동시킵니다.
        Dry-run 모드로 미리보기를 제공하고, 확인 다이얼로그를 표시한 후 실제 이동을 수행합니다.
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
        
        self._logger.info(f"파일 정리 시작: {len(self._duplicate_groups)}개 그룹")
        
        # Dry-run 모드로 미리보기
        preview_result = self._show_dry_run_preview()
        
        if preview_result is None:
            # 사용자가 취소
            return
        
        # 확인 다이얼로그
        confirmed = self._confirm_file_organization(preview_result)
        
        if not confirmed:
            return
        
        # 실제 파일 이동 수행
        self._execute_file_organization()
    
    def _show_dry_run_preview(self) -> Optional[dict[str, Any]]:
        """Dry-run 모드로 파일 이동 미리보기를 수행합니다.
        
        Returns:
            정리 결과 딕셔너리 (moved_count, failed_count, moved_files 등)
            사용자가 취소하면 None
        """
        try:
            self.status_label.setText("파일 정리 미리보기 중...")
            self.duplicate_check_btn.setEnabled(False)
            
            organizer = FileOrganizer(self.folder_path)
            result = organizer.organize_duplicates(self._duplicate_groups, dry_run=True)
            
            self.status_label.setText("미리보기 완료")
            self.duplicate_check_btn.setEnabled(True)
            
            return result
            
        except Exception as e:
            self._logger.error(f"Dry-run 미리보기 오류: {e}", exc_info=True)
            self.status_label.setText("미리보기 오류 발생")
            self.duplicate_check_btn.setEnabled(True)
            
            QMessageBox.critical(
                self,
                "오류",
                f"파일 정리 미리보기 중 오류가 발생했습니다:\n{str(e)}"
            )
            return None
    
    def _confirm_file_organization(self, preview_result: dict[str, Any]) -> bool:
        """파일 정리 확인 다이얼로그를 표시합니다.
        
        Args:
            preview_result: Dry-run 결과 딕셔너리
        
        Returns:
            사용자가 확인하면 True, 취소하면 False
        """
        moved_count = preview_result.get("moved_count", 0)
        failed_count = preview_result.get("failed_count", 0)
        moved_files = preview_result.get("moved_files", [])
        
        if moved_count == 0:
            QMessageBox.information(
                self,
                "알림",
                "이동할 파일이 없습니다."
            )
            return False
        
        # 이동할 파일 목록 생성 (최대 20개만 표시)
        file_list_text = ""
        display_count = min(20, len(moved_files))
        for i, file_info in enumerate(moved_files[:display_count], 1):
            source_path = Path(file_info["source"])
            file_list_text += f"{i}. {source_path.name}\n"
        
        if len(moved_files) > display_count:
            file_list_text += f"\n... 외 {len(moved_files) - display_count}개 파일"
        
        message = (
            f"다음 파일들을 'old_versions' 폴더로 이동시킵니다:\n\n"
            f"이동할 파일: {moved_count}개\n"
            f"예상 실패: {failed_count}개\n\n"
            f"파일 목록:\n{file_list_text}\n\n"
            f"계속하시겠습니까?"
        )
        
        reply = QMessageBox.question(
            self,
            "파일 정리 확인",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def _execute_file_organization(self) -> None:
        """실제 파일 이동을 수행합니다.
        
        백그라운드 스레드에서 실행하여 UI 프리징을 방지합니다.
        """
        try:
            self.status_label.setText("파일 이동 중...")
            self.duplicate_check_btn.setEnabled(False)
            self.duplicate_check_btn.setText("이동 중...")
            
            # 동기적으로 실행 (파일 이동은 빠르므로)
            organizer = FileOrganizer(self.folder_path)
            result = organizer.organize_duplicates(self._duplicate_groups, dry_run=False)
            
            # 결과 처리
            moved_count = result.get("moved_count", 0)
            failed_count = result.get("failed_count", 0)
            failed_files = result.get("failed_files", [])
            
            if failed_count > 0:
                failed_list = "\n".join(failed_files[:10])
                if len(failed_files) > 10:
                    failed_list += f"\n... 외 {len(failed_files) - 10}개"
                
                QMessageBox.warning(
                    self,
                    "파일 정리 완료 (일부 실패)",
                    f"파일 정리가 완료되었습니다.\n\n"
                    f"이동 성공: {moved_count}개\n"
                    f"이동 실패: {failed_count}개\n\n"
                    f"실패한 파일:\n{failed_list}"
                )
            else:
                QMessageBox.information(
                    self,
                    "파일 정리 완료",
                    f"파일 정리가 완료되었습니다.\n\n"
                    f"이동된 파일: {moved_count}개"
                )
            
            self.status_label.setText(f"파일 정리 완료: {moved_count}개 이동")
            
            # UI 업데이트 (이동된 파일 제거 또는 상태 업데이트)
            self._update_ui_after_file_organization(result)
            
        except Exception as e:
            self._logger.error(f"파일 정리 실행 오류: {e}", exc_info=True)
            self.status_label.setText("파일 정리 오류 발생")
            
            QMessageBox.critical(
                self,
                "오류",
                f"파일 정리 중 오류가 발생했습니다:\n{str(e)}"
            )
        finally:
            self.duplicate_check_btn.setEnabled(True)
            self.duplicate_check_btn.setText("파일 정리 실행")
    
    def _update_ui_after_file_organization(self, result: dict[str, Any]) -> None:
        """파일 이동 완료 후 UI를 업데이트합니다.
        
        Args:
            result: 파일 정리 결과 딕셔너리
        """
        moved_files = result.get("moved_files", [])
        if not moved_files:
            return
        
        # 이동된 파일 경로 집합 생성
        moved_paths = {Path(info["source"]) for info in moved_files}
        
        # 테이블에서 이동된 파일 제거 또는 상태 업데이트
        rows_to_remove: list[tuple[int, str]] = []  # (row, file_path_str)
        for row in range(self.file_table.rowCount()):
            name_item = self.file_table.item(row, 0)
            if name_item is None:
                continue
            
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                continue
            
            file_path = Path(file_path_str)
            if file_path in moved_paths:
                rows_to_remove.append((row, file_path_str))
        
        # 역순으로 제거 (인덱스 변경 방지)
        for row, file_path_str in reversed(rows_to_remove):
            self.file_table.removeRow(row)
        
        # scanned_files에서도 제거
        moved_path_strs = {str(Path(info["source"])) for info in moved_files}
        self.scanned_files = [
            f for f in self.scanned_files
            if str(f.path) not in moved_path_strs
        ]
        
        # 중복 그룹 정보 초기화 (이미 이동 완료)
        self._duplicate_groups = []
        
        # 버튼 상태 복원
        self.duplicate_check_btn.setText("중복 검사")
        self.duplicate_check_btn.clicked.disconnect()
        self.duplicate_check_btn.clicked.connect(self._on_duplicate_check)
        
        self._logger.info(f"UI 업데이트 완료: {len(rows_to_remove)}개 행 제거")

