"""ResultSignals - Qt Signals 정의."""

from PySide6.QtCore import QObject, Signal
from pathlib import Path
from typing import Optional
from gui.view_models.file_row import FileRow
from domain.models.duplicate_group import DuplicateGroup
from domain.models.integrity_issue import IntegrityIssue
from domain.models.action_plan import ActionPlan


class ResultSignals(QObject):
    """결과 관련 Signal 정의.
    
    Worker에서 UI로 결과를 전달하는 Signal들.
    """
    
    # 스캔 진행 상황
    scan_progress = Signal(str, int, int, str)  # stage, done, total, current_path
    
    # 행 추가/업데이트 (슬림한 FileRow만 전달)
    rows_appended = Signal(list)  # list[FileRow]
    rows_updated = Signal(list)  # list[FileRow]
    
    # 그룹/이슈/플랜 업데이트
    groups_updated = Signal(list)  # list[DuplicateGroup]
    issues_updated = Signal(list)  # list[IntegrityIssue]
    plan_updated = Signal(object)  # ActionPlan
    
    # 로그 이벤트
    log_event = Signal(str, str, Optional[int])  # level, msg, file_id

