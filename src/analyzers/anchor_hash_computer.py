"""
앵커 해시 계산기 모듈

파일의 앵커 해시를 병렬로 계산하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.hash_calculator import compute_anchor_hashes
from utils.constants import (
    MAX_WORKER_THREADS,
    PROGRESS_UPDATE_INTERVAL,
    DEFAULT_ENCODING,
    ENCODING_NOT_DETECTED,
)


class AnchorHashComputer:
    """앵커 해시 계산기 클래스.
    
    파일의 앵커 해시를 병렬로 계산합니다.
    ThreadPoolExecutor를 사용하여 성능을 최적화합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _progress_callback: 진행 상황 업데이트 콜백 함수 (선택적)
    """
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """AnchorHashComputer 초기화.
        
        Args:
            progress_callback: 진행 상황 업데이트 콜백 함수 (message: str) -> None
        """
        self._logger = get_logger("AnchorHashComputer")
        self._progress_callback = progress_callback
    
    def _update_progress(self, message: str) -> None:
        """진행 상황을 업데이트합니다.
        
        Args:
            message: 진행 상황 메시지
        """
        if self._progress_callback:
            self._progress_callback(message)
        self._logger.debug(message)
    
    def compute_hashes(
        self,
        records: list[FileRecord]
    ) -> list[FileRecord]:
        """파일 레코드들의 앵커 해시를 병렬로 계산합니다.
        
        앵커 해시가 없는 레코드만 계산하고, 결과를 업데이트합니다.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            앵커 해시가 계산된 FileRecord 리스트
        """
        # 앵커 해시가 필요한 레코드만 필터링
        records_needing_hash = [
            (idx, record) for idx, record in enumerate(records)
            if not record.anchor_hashes
        ]
        
        if not records_needing_hash:
            # 모든 레코드에 앵커 해시가 있으면 그대로 반환
            return list(records)
        
        total_records = len(records)
        records_with_hashes = list(records)  # 원본 복사
        
        # 병렬 처리로 앵커 해시 계산
        max_workers = min(
            os.cpu_count() or 4,
            len(records_needing_hash),
            MAX_WORKER_THREADS
        )
        self._logger.debug(
            f"병렬 앵커 해시 계산 시작: {len(records_needing_hash)}개 파일, {max_workers}개 스레드"
        )
        
        def _compute_hash_for_record(
            item: tuple[int, FileRecord]
        ) -> tuple[int, FileRecord, Optional[dict[str, str]]]:
            """레코드의 앵커 해시를 계산하는 헬퍼 함수."""
            idx, record = item
            try:
                # encoding이 "-"인 경우 기본값 사용 (스캔 단계에서 확정되어야 하지만 안전장치)
                encoding = (
                    record.encoding
                    if record.encoding != ENCODING_NOT_DETECTED
                    else DEFAULT_ENCODING
                )
                anchor_hashes = compute_anchor_hashes(record.path, encoding)
                return (idx, record, anchor_hashes)
            except Exception as e:
                self._logger.warning(f"앵커 해시 계산 실패 (스킵): {record.path} - {e}")
                return (idx, record, None)
        
        # ThreadPoolExecutor로 병렬 처리
        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_record = {
                executor.submit(_compute_hash_for_record, item): item[0]
                for item in records_needing_hash
            }
            
            for future in as_completed(future_to_record):
                try:
                    idx, record, anchor_hashes = future.result()
                    if anchor_hashes:
                        # FileRecord 업데이트
                        records_with_hashes[idx] = record.model_copy(
                            update={"anchor_hashes": anchor_hashes}
                        )
                    
                    completed_count += 1
                    # 진행 상황 업데이트 (PROGRESS_UPDATE_INTERVAL개마다 또는 마지막)
                    if (
                        completed_count % PROGRESS_UPDATE_INTERVAL == 0
                        or completed_count == len(records_needing_hash)
                    ):
                        self._update_progress(
                            f"앵커 해시 계산 중: {completed_count}/{len(records_needing_hash)} "
                            f"(전체 {total_records}개 중)"
                        )
                except Exception as e:
                    self._logger.error(f"앵커 해시 계산 중 예외 발생: {e}", exc_info=True)
        
        return records_with_hashes

