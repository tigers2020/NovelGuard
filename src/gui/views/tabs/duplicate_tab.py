"""중복 파일 정리 탭."""
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.ports.index_repository import IIndexRepository
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase
from application.utils.debug_logger import debug_step
from application.utils.duplicate_json import generate_duplicate_json_filename, save_duplicate_result_to_json
from gui.models.app_state import AppState
from gui.view_models.duplicate_view_model import DuplicateViewModel
from gui.views.components.dry_run_preview_dialog import DryRunPreviewDialog
from gui.views.tabs.base_tab import BaseTab
from gui.workers.file_move_worker import FileMoveWorker

logger = logging.getLogger(__name__)


class DuplicateTab(BaseTab):
    """중복 파일 정리 탭."""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        job_manager: Optional[IJobRunner] = None,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """중복 탭 초기화.
        
        Args:
            parent: 부모 위젯.
            job_manager: Job 관리자 (선택적).
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        self._job_manager = job_manager
        self._index_repository = index_repository
        self._log_sink = log_sink
        
        debug_step(self._log_sink, "duplicate_tab_init")
        
        # ViewModel을 먼저 생성
        self._view_model = DuplicateViewModel(
            parent=None,
            job_manager=job_manager,
            index_repository=index_repository,
            log_sink=log_sink
        )
        
        self._app_state: Optional[AppState] = None
        self._move_worker: Optional[FileMoveWorker] = None
        
        super().__init__(parent)
        
        # AppState 가져오기
        self._app_state = self._get_app_state()
        
        # ViewModel의 parent 설정
        self._view_model.setParent(self)
        
        # ViewModel 시그널 연결 (컴포넌트와 무관한 시그널만)
        self._view_model.progress_updated.connect(self._on_progress_updated)
        self._view_model.duplicate_completed.connect(self._on_duplicate_completed)
        self._view_model.duplicate_error.connect(self._on_duplicate_error)
        self._view_model.results_updated.connect(self._on_results_updated)
    
    def _get_app_state(self) -> AppState:
        """AppState 가져오기."""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_app_state'):
                return parent._app_state
            parent = parent.parent()
        # 기본값으로 새로 생성
        return AppState()
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "🔍 중복 파일 정리"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # AppState 가져오기 (super().__init__ 이후이므로 가능)
        if self._app_state is None:
            self._app_state = self._get_app_state()
        
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        detect_btn = QPushButton("중복 탐지 시작")
        detect_btn.setObjectName("btnPrimary")
        detect_btn.clicked.connect(self._on_start_detection)
        layout.addWidget(detect_btn)
        
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        dry_run_btn.clicked.connect(self._on_dry_run)
        layout.addWidget(dry_run_btn)
        
        apply_btn = QPushButton("적용하기")
        apply_btn.setObjectName("btnSuccess")
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)
        
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
        
        progress_title = QLabel("중복 탐지 진행 중...")
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
    
    def _on_start_detection(self) -> None:
        """중복 탐지 시작 버튼 핸들러."""
        debug_step(self._log_sink, "duplicate_tab_start_detection")
        self._view_model.start_duplicate_detection()
    
    def _on_progress_updated(self, progress: int, message: str) -> None:
        """진행률 업데이트 핸들러."""
        # Indeterminate 진행률
        self._progress_bar.setRange(0, 0)
        self._progress_info.setText(message)
        self._progress_percent.setText("")
    
    def _on_duplicate_completed(self, results: list) -> None:
        """중복 탐지 완료 핸들러."""
        debug_step(
            self._log_sink,
            "duplicate_tab_completed",
            {"results_count": len(results)}
        )
        
        # 프로그레스 바를 normal 모드로 복원
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        self._progress_info.setText(f"완료: {len(results)}개 그룹")
        
        # FileDataStore에 중복 그룹 정보 마킹 (배치 처리로 UI 프리징 방지)
        if self._app_state:
            file_data_store = self._app_state.file_data_store
            
            # 배치 업데이트를 위한 업데이트 리스트 생성
            # file_id 중복 제거를 위해 dict 사용 (마지막 처리된 그룹 정보만 유지)
            # 정규화로 이미 중복이 제거되어 있지만, 이중 안전장치
            batch_updates_dict: dict[int, tuple[int, Optional[int], bool, Optional[float]]] = {}
            
            for result in results:
                # evidence에서 similarity 추출 (near duplicate의 경우)
                evidence = result.evidence or {}
                similarity_score = None
                if result.duplicate_type == "near":
                    # near duplicate인 경우 evidence에서 similarity 값 추출
                    similarity_score = evidence.get("similarity")
                    if similarity_score is None:
                        # fallback: confidence를 similarity로 사용 (정확도 낮음)
                        similarity_score = result.confidence
                
                for file_id in result.file_ids:
                    is_canonical = (file_id == result.recommended_keeper_id) if result.recommended_keeper_id else False
                    # file_id를 키로 사용하여 중복 제거 (마지막 그룹 정보가 우선)
                    batch_updates_dict[file_id] = (
                        file_id,
                        result.group_id,
                        is_canonical,
                        similarity_score  # confidence가 아닌 실제 similarity 값 사용
                    )
            
            # dict에서 리스트로 변환
            batch_updates = list(batch_updates_dict.values())
            
            # 배치 업데이트 (시그널을 한 번만 emit하여 UI 프리징 방지)
            if batch_updates:
                file_data_store.set_duplicate_groups_batch(batch_updates)
            
            # 중복 탐지 결과를 JSON 파일로 저장
            self._save_duplicate_result_to_json(results, file_data_store)
    
    def _save_duplicate_result_to_json(self, results: list, file_data_store) -> None:
        """중복 탐지 결과를 JSON 파일로 저장.
        
        Args:
            results: 중복 그룹 결과 리스트.
            file_data_store: 파일 데이터 저장소.
        
        저장 실패 시에도 중복 탐지 완료 처리는 계속 진행됩니다 (로깅만 기록).
        """
        debug_step(
            self._log_sink,
            "duplicate_tab_save_result_start",
            {"results_count": len(results)}
        )
        
        try:
            # 프로젝트 루트의 SAVE 폴더에 절대 경로로 저장
            # duplicate_tab.py: src/gui/views/tabs/duplicate_tab.py
            # 프로젝트 루트: parent 5단계 위
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            save_dir = project_root / "SAVE"
            
            # 파일명 생성
            filename = generate_duplicate_json_filename()
            output_path = save_dir.resolve() / filename
            
            # 스캔 폴더 가져오기
            scan_folder = file_data_store.scan_folder if file_data_store else None
            
            # JSON 파일로 저장
            save_duplicate_result_to_json(results, output_path, file_data_store, scan_folder)
            
            debug_step(
                self._log_sink,
                "duplicate_tab_save_result_success",
                {"output_path": str(output_path)}
            )
            
            logger.info(f"중복 탐지 결과 JSON 저장 완료: {output_path}")
        
        except Exception as e:
            # JSON 저장 실패는 중복 탐지 완료 처리에 영향을 주지 않음
            debug_step(
                self._log_sink,
                "duplicate_tab_save_result_error",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            logger.warning(f"중복 탐지 결과 JSON 저장 실패 (중복 탐지 완료는 정상 처리됨): {e}", exc_info=True)
    
    def _on_duplicate_error(self, error_message: str) -> None:
        """중복 탐지 오류 핸들러."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_percent.setText("0%")
        self._progress_info.setText(f"오류: {error_message}")
    
    def _on_results_updated(self) -> None:
        """결과 업데이트 핸들러."""
        # FileListTableWidget이 FileDataStore 시그널을 통해 자동으로 업데이트됨
        pass
    
    def _on_dry_run(self) -> None:
        """Dry Run 버튼 핸들러."""
        debug_step(self._log_sink, "duplicate_tab_dry_run")
        
        if not self._app_state:
            QMessageBox.warning(self, "오류", "앱 상태를 가져올 수 없습니다.")
            return
        
        file_data_store = self._app_state.file_data_store
        scan_folder = file_data_store.scan_folder
        
        if not scan_folder:
            QMessageBox.warning(self, "오류", "스캔 폴더가 설정되지 않았습니다. 먼저 스캔을 실행하세요.")
            return
        
        # UseCase 생성 및 실행 (dry_run=True)
        use_case = MoveDuplicateFilesUseCase(file_data_store, self._log_sink)
        operations = use_case.execute(scan_folder, dry_run=True)
        
        if not operations:
            QMessageBox.information(self, "Dry Run", "이동할 파일이 없습니다.")
            return
        
        # 미리보기 다이얼로그 표시
        dialog = DryRunPreviewDialog(operations, scan_folder, self)
        dialog.exec()
    
    def _on_apply(self) -> None:
        """적용하기 버튼 핸들러."""
        debug_step(self._log_sink, "duplicate_tab_apply")
        
        if not self._app_state:
            QMessageBox.warning(self, "오류", "앱 상태를 가져올 수 없습니다.")
            return
        
        file_data_store = self._app_state.file_data_store
        scan_folder = file_data_store.scan_folder
        
        if not scan_folder:
            QMessageBox.warning(self, "오류", "스캔 폴더가 설정되지 않았습니다. 먼저 스캔을 실행하세요.")
            return
        
        # UseCase로 이동할 파일 확인
        use_case = MoveDuplicateFilesUseCase(file_data_store, self._log_sink)
        operations = use_case.execute(scan_folder, dry_run=True)
        
        if not operations:
            QMessageBox.information(self, "적용하기", "이동할 파일이 없습니다.")
            return
        
        # 확인 다이얼로그
        reply = QMessageBox.question(
            self,
            "적용하기",
            f"총 {len(operations)}개 파일을 duplicate/ 폴더로 이동합니다.\n"
            "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Worker 생성 및 시작
        self._move_worker = FileMoveWorker(use_case, scan_folder, self._log_sink, self)
        self._move_worker.move_progress.connect(self._on_move_progress)
        self._move_worker.move_completed.connect(self._on_move_completed)
        self._move_worker.move_error.connect(self._on_move_error)
        self._move_worker.start()
        
        # 프로그레스 표시
        self._progress_bar.setRange(0, 0)  # Indeterminate
        self._progress_info.setText("파일 이동 중...")
        self._progress_percent.setText("")
    
    def _on_move_progress(self, processed_count: int, total_count: int, current_file: str) -> None:
        """파일 이동 진행률 업데이트 핸들러."""
        if total_count > 0:
            self._progress_bar.setRange(0, total_count)
            self._progress_bar.setValue(processed_count)
            percent = int((processed_count / total_count) * 100)
            self._progress_percent.setText(f"{percent}%")
        self._progress_info.setText(f"이동 중: {Path(current_file).name}")
    
    def _on_move_completed(self, moved_count: int, error_count: int, error_list: list, moved_file_ids: list[int]) -> None:
        """파일 이동 완료 핸들러."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_percent.setText("100%")
        
        # FileDataStore에서 이동된 파일 제거
        if moved_file_ids and self._app_state:
            file_data_store = self._app_state.file_data_store
            file_data_store.remove_files(moved_file_ids)
        
        if error_count == 0:
            self._progress_info.setText(f"완료: {moved_count}개 파일 이동 완료")
            QMessageBox.information(
                self,
                "완료",
                f"{moved_count}개 파일이 duplicate/ 폴더로 이동되었습니다."
            )
        else:
            self._progress_info.setText(f"완료: {moved_count}개 이동, {error_count}개 실패")
            error_details = "\n".join([f"- {path}: {msg}" for path, msg in error_list[:10]])
            if len(error_list) > 10:
                error_details += f"\n... 외 {len(error_list) - 10}개"
            QMessageBox.warning(
                self,
                "부분 완료",
                f"{moved_count}개 파일 이동 완료, {error_count}개 파일 이동 실패:\n\n{error_details}"
            )
        
        # Worker 정리
        if self._move_worker:
            self._move_worker.deleteLater()
            self._move_worker = None
    
    def _on_move_error(self, error_message: str) -> None:
        """파일 이동 오류 핸들러."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_percent.setText("0%")
        self._progress_info.setText(f"오류: {error_message}")
        QMessageBox.critical(self, "오류", f"파일 이동 중 오류가 발생했습니다:\n\n{error_message}")
        
        # Worker 정리
        if self._move_worker:
            self._move_worker.deleteLater()
            self._move_worker = None
    