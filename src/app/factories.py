"""Composition Root 팩토리 함수들.

도메인 서비스·infrastructure 어댑터를 조립하여 application 유스케이스에
필요한 객체 그래프를 생성한다. `app/main.py`에서 팩토리를 QtJobManager에 주입한다.
"""

from typing import Optional

from application.ports.file_data_store import IFileDataStore
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)
from domain.services.blocking_service import BlockingService
from domain.services.containment_detector import ContainmentDetector
from domain.services.exact_duplicate_detector import ExactDuplicateDetector
from domain.services.filename_parser import FilenameParser
from infrastructure.hashing.hash_service_adapter import HashServiceAdapter


def create_duplicate_detection_pipeline(
    index_repository: IIndexRepository,
    file_data_store: Optional[IFileDataStore] = None,
    log_sink: Optional[ILogSink] = None,
) -> DuplicateDetectionPipeline:
    """중복 탐지 파이프라인을 조립하여 반환한다."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    hash_service = HashServiceAdapter()
    exact_detector = ExactDuplicateDetector(hash_service=hash_service)

    return DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository,
        file_data_store=file_data_store,
        log_sink=log_sink,
        exact_detector=exact_detector,
    )
