"""ResultEventRouter - Signal → Store → Index → Models 라우팅."""

from typing import Optional
from PySide6.QtCore import QObject
from gui.stores.result_store import ResultStore
from gui.signals.result_signals import ResultSignals
from common.logging import setup_logging

logger = setup_logging()


class ResultEventRouter(QObject):
    """결과 이벤트 라우터.
    
    Signal → Store → Index → Models 순서로 갱신.
    """
    
    def __init__(
        self,
        store: ResultStore,
        index_manager: "ResultIndexManager",
        table_model: "ResultTableModel",
        signals: ResultSignals,
        batcher: Optional[object] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """ResultEventRouter 초기화.
        
        Args:
            store: ResultStore
            index_manager: ResultIndexManager
            table_model: ResultTableModel
            signals: ResultSignals
            batcher: UIBatcher (선택적)
            parent: 부모 객체
        """
        super().__init__(parent)
        
        self.store = store
        self.index_manager = index_manager
        self.table_model = table_model
        self.signals = signals
        self.batcher = batcher
        
        # Signal 연결
        if batcher:
            # UIBatcher를 통해 배치 처리
            signals.rows_appended.connect(batcher.enqueue_append)
            signals.rows_updated.connect(batcher.enqueue_update)
            batcher.rows_appended.connect(self._on_rows_appended)
            batcher.rows_updated.connect(self._on_rows_updated)
        else:
            # 직접 처리
            signals.rows_appended.connect(self._on_rows_appended)
            signals.rows_updated.connect(self._on_rows_updated)
        
        signals.groups_updated.connect(self._on_groups_updated)
        signals.issues_updated.connect(self._on_issues_updated)
        signals.plan_updated.connect(self._on_plan_updated)
    
    def _on_rows_appended(self, rows: list) -> None:
        """행 추가 처리.
        
        Args:
            rows: 추가할 FileRow 리스트
        """
        # 1. Store에 반영
        self.store.add_rows(rows)
        
        # 2. Index 업데이트
        self.index_manager.add_rows(rows)
        
        # 3. Model에 통지
        self.table_model.appendRows(rows)
    
    def _on_rows_updated(self, rows: list) -> None:
        """행 업데이트 처리.
        
        Args:
            rows: 업데이트할 FileRow 리스트
        """
        # 1. Store에 반영
        self.store.update_rows(rows)
        
        # 2. Index 업데이트
        self.index_manager.update_rows(rows)
        
        # 3. Model에 통지
        self.table_model.updateRows(rows)
    
    def _on_groups_updated(self, groups: list) -> None:
        """그룹 업데이트 처리.
        
        Args:
            groups: 추가할 DuplicateGroup 리스트
        """
        # Store에 반영
        self.store.add_groups(groups)
        
        # Index 업데이트
        self.index_manager.update_groups(groups)
    
    def _on_issues_updated(self, issues: list) -> None:
        """이슈 업데이트 처리.
        
        Args:
            issues: 추가할 IntegrityIssue 리스트
        """
        # Store에 반영
        self.store.add_issues(issues)
        
        # Index 업데이트
        self.index_manager.update_issues(issues)
    
    def _on_plan_updated(self, plan: object) -> None:
        """플랜 업데이트 처리.
        
        Args:
            plan: ActionPlan
        """
        # Store에 반영
        self.store.set_plan(plan)
