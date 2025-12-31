"""
파일 정리 워크플로우 모듈

파일 정리 워크플로우를 관리하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QTableWidget

from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger
from utils.file_organizer import FileOrganizer
from gui.managers.scan_result_manager import ScanResultManager


class FileOrganizationWorkflow:
    """파일 정리 워크플로우 클래스.
    
    파일 정리 워크플로우를 관리합니다.
    Dry-run 미리보기, 확인 다이얼로그, 실제 파일 이동을 순차적으로 수행합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _root_folder: 루트 폴더 경로
        _organizer: FileOrganizer 인스턴스
        _scan_result_manager: ScanResultManager 인스턴스
        _table: 테이블 위젯 (UI 업데이트용)
        _status_callback: 상태 업데이트 콜백 함수
        _button_callback: 버튼 상태 업데이트 콜백 함수
    """
    
    def __init__(
        self,
        root_folder: Path,
        scan_result_manager: ScanResultManager,
        table: Optional[QTableWidget] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        button_callback: Optional[Callable[[bool, str], None]] = None
    ) -> None:
        """FileOrganizationWorkflow 초기화.
        
        Args:
            root_folder: 파일 정리를 수행할 루트 폴더 경로
            scan_result_manager: 스캔 결과 매니저
            table: 테이블 위젯 (UI 업데이트용, 선택적)
            status_callback: 상태 업데이트 콜백 함수 (message: str) -> None
            button_callback: 버튼 상태 업데이트 콜백 함수 (enabled: bool, text: str) -> None
        """
        self._logger = get_logger("FileOrganizationWorkflow")
        self._root_folder = root_folder
        self._organizer = FileOrganizer(root_folder)
        self._scan_result_manager = scan_result_manager
        self._table = table
        self._status_callback = status_callback
        self._button_callback = button_callback
    
    def _update_status(self, message: str) -> None:
        """상태를 업데이트합니다."""
        if self._status_callback:
            self._status_callback(message)
        self._logger.debug(message)
    
    def _update_button(self, enabled: bool, text: str) -> None:
        """버튼 상태를 업데이트합니다."""
        if self._button_callback:
            self._button_callback(enabled, text)
    
    def execute(
        self,
        duplicate_groups: list[DuplicateGroup],
        parent_widget: Optional[Any] = None
    ) -> bool:
        """파일 정리 워크플로우를 실행합니다.
        
        Dry-run 모드로 미리보기를 제공하고, 확인 다이얼로그를 표시한 후
        실제 파일 이동을 수행합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트
            parent_widget: 부모 위젯 (메시지박스용, 선택적)
        
        Returns:
            파일 정리가 성공적으로 완료되면 True, 취소되면 False
        """
        if not duplicate_groups:
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "경고",
                    "정리할 중복 그룹이 없습니다. 먼저 중복 검사를 진행해주세요."
                )
            return False
        
        self._logger.info(f"파일 정리 워크플로우 시작: {len(duplicate_groups)}개 그룹")
        
        # Dry-run 모드로 미리보기
        preview_result = self._show_dry_run_preview(duplicate_groups)
        
        if preview_result is None:
            # 사용자가 취소 또는 오류 발생
            return False
        
        # 확인 다이얼로그
        confirmed = self._confirm_file_organization(preview_result, parent_widget)
        
        if not confirmed:
            return False
        
        # 실제 파일 이동 수행
        return self._execute_file_organization(duplicate_groups, parent_widget)
    
    def _show_dry_run_preview(
        self,
        duplicate_groups: list[DuplicateGroup]
    ) -> Optional[dict[str, Any]]:
        """Dry-run 모드로 파일 이동 미리보기를 수행합니다 (그룹 포함).
        
        Args:
            duplicate_groups: 중복 그룹 리스트
        
        Returns:
            정리 결과 딕셔너리 (moved_count, failed_count, moved_files 등)
            오류 발생 시 None
        """
        try:
            self._update_status("파일 정리 미리보기 중...")
            self._update_button(False, "미리보기 중...")
            
            result = self._organizer.organize_duplicates(duplicate_groups, dry_run=True)
            
            self._update_status("미리보기 완료")
            self._update_button(True, "파일 정리 실행")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Dry-run 미리보기 오류: {e}", exc_info=True)
            self._update_status("미리보기 오류 발생")
            self._update_button(True, "파일 정리 실행")
            return None
    
    def _confirm_file_organization(
        self,
        preview_result: dict[str, Any],
        parent_widget: Optional[Any] = None
    ) -> bool:
        """파일 정리 확인 다이얼로그를 표시합니다.
        
        Args:
            preview_result: Dry-run 결과 딕셔너리
            parent_widget: 부모 위젯 (메시지박스용, 선택적)
        
        Returns:
            사용자가 확인하면 True, 취소하면 False
        """
        moved_count = preview_result.get("moved_count", 0)
        failed_count = preview_result.get("failed_count", 0)
        moved_files = preview_result.get("moved_files", [])
        
        if moved_count == 0:
            if parent_widget:
                QMessageBox.information(
                    parent_widget,
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
        
        if not parent_widget:
            # 부모 위젯이 없으면 기본값으로 True 반환 (테스트용)
            return True
        
        reply = QMessageBox.question(
            parent_widget,
            "파일 정리 확인",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def _execute_file_organization(
        self,
        duplicate_groups: list[DuplicateGroup],
        parent_widget: Optional[Any] = None
    ) -> bool:
        """실제 파일 이동을 수행합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트
            parent_widget: 부모 위젯 (메시지박스용, 선택적)
        
        Returns:
            파일 정리가 성공적으로 완료되면 True
        """
        try:
            self._update_status("파일 이동 중...")
            self._update_button(False, "이동 중...")
            
            # 동기적으로 실행 (파일 이동은 빠르므로)
            result = self._organizer.organize_duplicates(duplicate_groups, dry_run=False)
            
            # 결과 처리
            moved_count = result.get("moved_count", 0)
            failed_count = result.get("failed_count", 0)
            failed_files = result.get("failed_files", [])
            
            if failed_count > 0:
                failed_list = "\n".join(failed_files[:10])
                if len(failed_files) > 10:
                    failed_list += f"\n... 외 {len(failed_files) - 10}개"
                
                if parent_widget:
                    QMessageBox.warning(
                        parent_widget,
                        "파일 정리 완료 (일부 실패)",
                        f"파일 정리가 완료되었습니다.\n\n"
                        f"이동 성공: {moved_count}개\n"
                        f"이동 실패: {failed_count}개\n\n"
                        f"실패한 파일:\n{failed_list}"
                    )
            else:
                if parent_widget:
                    QMessageBox.information(
                        parent_widget,
                        "파일 정리 완료",
                        f"파일 정리가 완료되었습니다.\n\n"
                        f"이동된 파일: {moved_count}개"
                    )
            
            self._update_status(f"파일 정리 완료: {moved_count}개 이동")
            
            # UI 업데이트 (이동된 파일 제거 또는 상태 업데이트)
            self._update_ui_after_file_organization(result)
            
            return True
            
        except Exception as e:
            self._logger.error(f"파일 정리 실행 오류: {e}", exc_info=True)
            self._update_status("파일 정리 오류 발생")
            
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "오류",
                    f"파일 정리 중 오류가 발생했습니다:\n{str(e)}"
                )
            return False
        finally:
            self._update_button(True, "파일 정리 실행")
    
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
        
        # 테이블에서 이동된 파일 제거
        if self._table:
            rows_to_remove: list[tuple[int, str]] = []  # (row, file_path_str)
            for row in range(self._table.rowCount()):
                name_item = self._table.item(row, 0)
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
                self._table.removeRow(row)
        
        # scanned_files에서도 제거
        moved_path_strs = {str(Path(info["source"])) for info in moved_files}
        current_files = self._scan_result_manager.get_scanned_files()
        remaining_files = [
            f for f in current_files
            if str(f.path) not in moved_path_strs
        ]
        self._scan_result_manager.set_scan_results(remaining_files, self._root_folder)
        
        self._logger.info(f"UI 업데이트 완료: {len(moved_files)}개 파일 제거")

