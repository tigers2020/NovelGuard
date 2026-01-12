"""도메인 서비스."""
from domain.services.blocking_service import BlockingService  # noqa: F401
from domain.services.containment_detector import ContainmentDetector  # noqa: F401
from domain.services.filename_parser import FilenameParser  # noqa: F401
from domain.services.keeper_score_service import KeeperScoreService  # noqa: F401

# NOTE: ExactDuplicateDetector와 NearDuplicateDetector는 v2 기능 (IHashService/ISimHashService 필요)
# 현재는 미구현 의존성으로 인해 비활성화. 파일은 유지하되 export하지 않음.
# from domain.services.exact_duplicate_detector import ExactDuplicateDetector  # noqa: F401
# from domain.services.near_duplicate_detector import NearDuplicateDetector  # noqa: F401

__all__ = [
    "FilenameParser",
    "BlockingService",
    "ContainmentDetector",
    "KeeperScoreService",
    # "ExactDuplicateDetector",  # v2 기능 (비활성화)
    # "NearDuplicateDetector",  # v2 기능 (비활성화)
]
