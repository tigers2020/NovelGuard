"""
NovelGuard 메인 윈도우 모듈

PySide6를 사용한 기본 GUI 창을 제공합니다.
"""

from pathlib import Path
from typing import Optional
import logging

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
from PySide6.QtCore import Qt, QSettings, QTimer, QTimer

from models.file_record import FileRecord
from scanners.file_scanner import FileScannerThread
from analyzers.duplicate_analyzer_thread import DuplicateAnalyzerThread
from utils.formatters import format_file_size
from utils.logger import get_logger


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
        self._pending_duplicate_updates: list[tuple[int, str, bool]] = []  # (row, text, is_duplicate)
        
        self._init_ui()
        self._setup_layout()
        self._load_and_display_last_folder()
        
        self._logger.info("메인 윈도우 초기화 완료")
        
    def _init_ui(self) -> None:
        """UI 초기화."""
        self.setWindowTitle("NovelGuard - 텍스트 소설 파일 정리 도구")
        self.setMinimumSize(800, 600)
        
        # 중앙 위젯 생성
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
    def _setup_layout(self) -> None:
        """레이아웃 설정."""
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목 레이블
        title_label = QLabel("NovelGuard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title_label.font()
        font.setPointSize(24)
        font.setBold(True)
        title_label.setFont(font)
        main_layout.addWidget(title_label)
        
        # 부제목 레이블
        subtitle_label = QLabel("텍스트 소설 파일 정리 도구")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-size: 14px;")
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
        self.select_folder_btn.setMinimumWidth(120)
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        folder_select_layout.addWidget(self.select_folder_btn)
        
        folder_layout.addLayout(folder_select_layout)
        main_layout.addLayout(folder_layout)
        
        # 파일 목록 테이블
        table_label = QLabel("파일 목록:")
        table_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        main_layout.addWidget(table_label)
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["파일명", "파일 크기", "인코딩", "중복 여부", "무결성 상태"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setMinimumHeight(300)
        main_layout.addWidget(self.file_table)
        
        # 액션 버튼 섹션
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.scan_btn = QPushButton("스캔 시작")
        self.scan_btn.setMinimumWidth(120)
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._on_scan_start)
        action_layout.addWidget(self.scan_btn)
        
        self.duplicate_check_btn = QPushButton("중복 검사")
        self.duplicate_check_btn.setMinimumWidth(120)
        self.duplicate_check_btn.setMinimumHeight(40)
        self.duplicate_check_btn.setEnabled(False)
        self.duplicate_check_btn.clicked.connect(self._on_duplicate_check)
        action_layout.addWidget(self.duplicate_check_btn)
        
        self.integrity_check_btn = QPushButton("무결성 확인")
        self.integrity_check_btn.setMinimumWidth(120)
        self.integrity_check_btn.setMinimumHeight(40)
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
            # #region agent log
            import json
            import time
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "main_window.py:_on_duplicate_check",
                        "message": "Before thread creation",
                        "data": {"file_count": len(self.scanned_files), "timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            self.duplicate_analyzer_thread = DuplicateAnalyzerThread(self.scanned_files)
            self.duplicate_analyzer_thread.analysis_finished.connect(self._on_duplicate_analysis_finished)
            self.duplicate_analyzer_thread.analysis_error.connect(self._on_duplicate_analysis_error)
            self.duplicate_analyzer_thread.progress_updated.connect(self._on_duplicate_progress_updated)
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "main_window.py:_on_duplicate_check",
                        "message": "Before thread.start()",
                        "data": {"timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            self.duplicate_analyzer_thread.start()
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "main_window.py:_on_duplicate_check",
                        "message": "After thread.start()",
                        "data": {"is_running": self.duplicate_analyzer_thread.isRunning(), "timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
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
        """중복 분석 완료 시그널 핸들러.
        
        Args:
            duplicate_groups: 중복 그룹 리스트
        """
        # #region agent log
        import json
        import time
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "main_window.py:_on_duplicate_analysis_finished",
                    "message": "Signal received",
                    "data": {"groups_count": len(duplicate_groups), "timestamp": int(time.time() * 1000)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        self._logger.info(f"중복 분석 완료: {len(duplicate_groups)}개 그룹 발견")
        
        # #region agent log
        import json
        import time
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "G",
                    "location": "main_window.py:_on_duplicate_analysis_finished",
                    "message": "Before QTimer.singleShot",
                    "data": {"groups_count": len(duplicate_groups), "timestamp": int(time.time() * 1000)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        # 결과 업데이트를 이벤트 루프에 예약 (비동기 처리로 UI 반응성 유지)
        # QTimer.singleShot(0, ...)를 사용하여 현재 이벤트 루프 사이클이 끝난 후 실행
        QTimer.singleShot(0, lambda: self._update_duplicate_results(duplicate_groups))
        
        # #region agent log
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "G",
                    "location": "main_window.py:_on_duplicate_analysis_finished",
                    "message": "After QTimer.singleShot (signal handler returning)",
                    "data": {"timestamp": int(time.time() * 1000)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        # 결과 요약 표시
        total_duplicates = sum(len(group) for group in duplicate_groups)
        if duplicate_groups:
            self.status_label.setText(
                f"중복 검사 완료: {len(duplicate_groups)}개 그룹, "
                f"{total_duplicates}개 중복 파일 발견"
            )
            # QMessageBox는 모달이므로 나중에 표시 (UI 반응성 향상)
            QMessageBox.information(
                self,
                "중복 검사 완료",
                f"{len(duplicate_groups)}개의 중복 그룹을 발견했습니다.\n"
                f"총 {total_duplicates}개의 중복 파일이 있습니다."
            )
        else:
            self.status_label.setText("중복 검사 완료: 중복 파일 없음")
            QMessageBox.information(
                self,
                "중복 검사 완료",
                "중복 파일을 찾을 수 없습니다."
            )
        
        self.duplicate_check_btn.setEnabled(True)
        self.duplicate_check_btn.setText("중복 검사")
    
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
        # #region agent log
        import json
        import time
        start_time = time.time()
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "G",
                    "location": "main_window.py:_update_duplicate_results",
                    "message": "Update started (called from QTimer callback)",
                    "data": {"groups_count": len(duplicate_groups), "table_rows": self.file_table.rowCount(), "timestamp": int(time.time() * 1000)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
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
        
        # 업데이트할 항목 리스트 생성 (점진적 업데이트용)
        # 아이템 참조를 미리 저장하여 item() 호출 최소화
        self._pending_duplicate_updates = []
        for row in range(row_count):
            name_item, duplicate_item = cached_items[row]
            if name_item is None:
                continue
            
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                continue
            
            if file_path_str in path_to_group:
                group_num = path_to_group[file_path_str]
                self._pending_duplicate_updates.append((row, f"중복 (그룹 {group_num})", True, duplicate_item))
            else:
                self._pending_duplicate_updates.append((row, "정상", False, duplicate_item))
        
        # QTimer로 점진적 업데이트 (배치 크기: 200개씩, 더 큰 배치로 성능 향상)
        self._duplicate_update_index = 0
        batch_size = 200
        
        # #region agent log
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "F",
                    "location": "main_window.py:_update_duplicate_results",
                    "message": "Prepared updates",
                    "data": {"total_updates": len(self._pending_duplicate_updates), "batch_size": batch_size, "timestamp": int(time.time() * 1000)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        def update_batch() -> None:
            """배치 단위로 테이블 업데이트."""
            # #region agent log
            batch_start = time.time()
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "F",
                        "location": "main_window.py:_update_duplicate_results:update_batch",
                        "message": "Batch started",
                        "data": {"index": self._duplicate_update_index, "total": len(self._pending_duplicate_updates), "timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            end_idx = min(self._duplicate_update_index + batch_size, len(self._pending_duplicate_updates))
            
            # UI 업데이트 일시 중지 (성능 향상)
            self.file_table.setUpdatesEnabled(False)
            
            try:
                for i in range(self._duplicate_update_index, end_idx):
                    row, text, is_duplicate, duplicate_item = self._pending_duplicate_updates[i]
                    
                    # 중복 여부 컬럼 (인덱스 3) - 캐시된 아이템 사용
                    if duplicate_item is None:
                        duplicate_item = QTableWidgetItem()
                        self.file_table.setItem(row, 3, duplicate_item)
                        # 캐시 업데이트
                        self._pending_duplicate_updates[i] = (row, text, is_duplicate, duplicate_item)
                    
                    duplicate_item.setText(text)
                    if is_duplicate:
                        duplicate_item.setForeground(Qt.GlobalColor.red)
                    else:
                        duplicate_item.setForeground(Qt.GlobalColor.black)
            finally:
                # UI 업데이트 재개
                self.file_table.setUpdatesEnabled(True)
            
            batch_elapsed = (time.time() - batch_start) * 1000
            self._duplicate_update_index = end_idx
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "F",
                        "location": "main_window.py:_update_duplicate_results:update_batch",
                        "message": "Batch completed",
                        "data": {"index": self._duplicate_update_index, "total": len(self._pending_duplicate_updates), "batch_elapsed_ms": batch_elapsed, "timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            # 더 업데이트할 항목이 있으면 다음 배치 예약
            if self._duplicate_update_index < len(self._pending_duplicate_updates):
                QTimer.singleShot(5, update_batch)  # 5ms 후 다음 배치 (더 빠른 업데이트)
            else:
                # 모든 업데이트 완료
                elapsed = (time.time() - start_time) * 1000
                # #region agent log
                try:
                    with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "F",
                            "location": "main_window.py:_update_duplicate_results",
                            "message": "Update completed (progressive)",
                            "data": {"total_updates": len(self._pending_duplicate_updates), "elapsed_ms": elapsed, "timestamp": int(time.time() * 1000)},
                            "timestamp": int(time.time() * 1000)
                        }) + "\n")
                except: pass
                # #endregion
                self._pending_duplicate_updates = []
        
        # 첫 배치 시작 (즉시 실행)
        update_batch()
    
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

