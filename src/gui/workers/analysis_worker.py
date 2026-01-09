"""AnalysisWorker - 분석 Worker."""

from PySide6.QtCore import QThread
from usecases.find_duplicates import FindDuplicatesUseCase
from usecases.check_integrity import CheckIntegrityUseCase
from usecases.build_action_plan import BuildActionPlanUseCase
from gui.signals.result_signals import ResultSignals
from common.logging import setup_logging

logger = setup_logging()


class AnalysisWorker(QThread):
    """분석 Worker.
    
    중복 탐지, 무결성 검사, 액션 플랜 생성.
    """
    
    def __init__(
        self,
        duplicate_usecase: FindDuplicatesUseCase,
        integrity_usecase: CheckIntegrityUseCase,
        plan_usecase: BuildActionPlanUseCase,
        signals: ResultSignals,
        parent=None
    ) -> None:
        """AnalysisWorker 초기화.
        
        Args:
            duplicate_usecase: FindDuplicatesUseCase
            integrity_usecase: CheckIntegrityUseCase
            plan_usecase: BuildActionPlanUseCase
            signals: ResultSignals
            parent: 부모 객체
        """
        super().__init__(parent)
        self.duplicate_usecase = duplicate_usecase
        self.integrity_usecase = integrity_usecase
        self.plan_usecase = plan_usecase
        self.signals = signals
    
    def run(self) -> None:
        """Worker 실행."""
        try:
            # 중복 탐지
            self.signals.scan_progress.emit("중복 탐지 중", 0, 100, "")
            groups = self.duplicate_usecase.execute()
            self.signals.groups_updated.emit(groups)
            
            # 무결성 검사
            self.signals.scan_progress.emit("무결성 검사 중", 0, 100, "")
            issues = self.integrity_usecase.execute()
            self.signals.issues_updated.emit(issues)
            
            # 액션 플랜 생성
            self.signals.scan_progress.emit("액션 플랜 생성 중", 0, 100, "")
            plan = self.plan_usecase.execute(groups, issues)
            self.signals.plan_updated.emit(plan)
            
        except Exception as e:
            logger.error(f"분석 Worker 오류: {e}")
            self.signals.log_event.emit("ERROR", f"분석 실패: {e}", None)

