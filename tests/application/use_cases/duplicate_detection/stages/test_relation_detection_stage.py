"""RelationDetectionStage 테스트."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import PipelineContext
from application.use_cases.duplicate_detection.stages.relation_detection_stage import (
    RelationDetectionStage,
)
from domain.entities.file_entry import FileEntry
from domain.services.containment_detector import ContainmentDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.duplicate_relation import ContainmentRelation, VersionRelation
from domain.value_objects.filename_parse_result import FilenameParseResult


def test_relation_detection_stage_name():
    """RelationDetectionStage 이름 테스트."""
    containment_detector = ContainmentDetector()

    stage = RelationDetectionStage(containment_detector=containment_detector)

    assert stage.name == "관계 탐지"


def test_relation_detection_stage_execute_no_blocking_groups():
    """Blocking 그룹이 없는 경우 테스트."""
    containment_detector = ContainmentDetector()

    stage = RelationDetectionStage(containment_detector=containment_detector)

    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.blocking_groups = []

    result_context = stage.execute(context)

    assert result_context.results == []


def test_relation_detection_stage_execute_containment():
    """Containment 관계 탐지 테스트."""
    containment_detector = Mock(spec=ContainmentDetector)
    log_sink = Mock(spec=ILogSink)

    # Mock 파일 엔트리 생성
    file_entry1 = FileEntry(
        path=Path("test1.txt"), size=100, mtime=datetime.now(), extension=".txt", file_id=1
    )
    file_entry2 = FileEntry(
        path=Path("test2.txt"), size=200, mtime=datetime.now(), extension=".txt", file_id=2
    )

    # 범위가 있어야 containment 후보 쌍으로 비교됨 (1-10이 1-5를 포함)
    parse_result1 = FilenameParseResult(
        original_path=Path("test1.txt"),
        original_name="test1",
        series_title_norm="test",
        range_start=1,
        range_end=10,
        confidence=0.9,
    )
    parse_result2 = FilenameParseResult(
        original_path=Path("test2.txt"),
        original_name="test2",
        series_title_norm="test",
        range_start=1,
        range_end=5,
        confidence=0.9,
    )

    # Mock containment 관계
    containment_relation = ContainmentRelation(
        container_file_id=1, contained_file_id=2, evidence={"test": "evidence"}, confidence=0.9
    )
    containment_detector.detect_containment.return_value = containment_relation
    containment_detector.detect_version.return_value = None

    # BlockingGroup 생성
    blocking_group = BlockingGroup(
        series_title_norm="test", extension=".txt", file_ids=[1, 2]  # 원래 file_id
    )

    stage = RelationDetectionStage(containment_detector=containment_detector, log_sink=log_sink)

    request = DuplicateDetectionRequest(run_id=1, enable_containment=True, enable_version=False)
    context = PipelineContext(request=request)
    context.blocking_groups = [blocking_group]
    context.file_id_mapping = {1: 10, 2: 20}  # IndexRepository file_id -> FileDataStore file_id
    context.file_entries_map = {10: file_entry1, 20: file_entry2}
    context.parse_results = {1: parse_result1, 2: parse_result2}

    result_context = stage.execute(context)

    assert len(result_context.results) == 1
    assert result_context.results[0].duplicate_type == "containment"
    assert result_context.results[0].file_ids == [10, 20]  # FileDataStore file_id
    assert result_context.results[0].recommended_keeper_id == 10


def test_relation_detection_stage_execute_version():
    """Version 관계 탐지 테스트."""
    containment_detector = Mock(spec=ContainmentDetector)

    # Mock 파일 엔트리 생성
    file_entry1 = FileEntry(
        path=Path("test1.txt"), size=100, mtime=datetime.now(), extension=".txt", file_id=1
    )
    file_entry2 = FileEntry(
        path=Path("test2.txt"), size=200, mtime=datetime.now(), extension=".txt", file_id=2
    )

    parse_result1 = FilenameParseResult(
        original_path=Path("test1.txt"),
        original_name="test1",
        series_title_norm="test",
        confidence=0.9,
    )
    parse_result2 = FilenameParseResult(
        original_path=Path("test2.txt"),
        original_name="test2",
        series_title_norm="test",
        confidence=0.9,
    )

    # Mock version 관계
    version_relation = VersionRelation(
        newer_file_id=2, older_file_id=1, evidence={"test": "evidence"}, confidence=0.8
    )
    containment_detector.detect_containment.return_value = None
    containment_detector.detect_version.return_value = version_relation

    # BlockingGroup 생성
    blocking_group = BlockingGroup(series_title_norm="test", extension=".txt", file_ids=[1, 2])

    stage = RelationDetectionStage(containment_detector=containment_detector)

    request = DuplicateDetectionRequest(run_id=1, enable_containment=False, enable_version=True)
    context = PipelineContext(request=request)
    context.blocking_groups = [blocking_group]
    context.file_id_mapping = {1: 10, 2: 20}
    context.file_entries_map = {10: file_entry1, 20: file_entry2}
    context.parse_results = {1: parse_result1, 2: parse_result2}

    result_context = stage.execute(context)

    assert len(result_context.results) == 1
    assert result_context.results[0].duplicate_type == "version"
    assert result_context.results[0].file_ids == [20, 10]  # newer, older 순서
    assert result_context.results[0].recommended_keeper_id == 20  # newer


def test_version_pairs_skipped_when_bucket_over_cap(monkeypatch) -> None:
    """range_start 버킷이 cap을 넘으면 version 쌍 비교를 스킵한다."""
    from domain.value_objects import detection_config

    monkeypatch.setattr(
        detection_config.DetectionDefaults,
        "MAX_FILES_PER_BLOCKING_GROUP_FOR_VERSION_PAIRS",
        2,
    )

    containment_detector = Mock(spec=ContainmentDetector)
    containment_detector.detect_containment.return_value = None
    containment_detector.detect_version.return_value = None

    log_sink = Mock(spec=ILogSink)
    stage = RelationDetectionStage(containment_detector=containment_detector, log_sink=log_sink)

    store_ids = [10, 20, 30]
    entries = {
        fid: FileEntry(
            path=Path(f"t{fid}.txt"),
            size=100,
            mtime=datetime.now(),
            extension=".txt",
            file_id=fid,
        )
        for fid in store_ids
    }
    parses = {
        idx: FilenameParseResult(
            original_path=Path(f"t{idx}.txt"),
            original_name=f"t{idx}",
            series_title_norm="test",
            range_start=1,
            range_end=100 + idx,
            confidence=0.9,
        )
        for idx in (1, 2, 3)
    }

    blocking_group = BlockingGroup(series_title_norm="test", extension=".txt", file_ids=[1, 2, 3])
    request = DuplicateDetectionRequest(run_id=1, enable_containment=False, enable_version=True)
    context = PipelineContext(request=request)
    context.blocking_groups = [blocking_group]
    context.file_id_mapping = {1: 10, 2: 20, 3: 30}
    context.file_entries_map = entries
    context.parse_results = parses

    result_context = stage.execute(context)

    assert result_context.results == []
    containment_detector.detect_version.assert_not_called()


def test_relation_detection_stage_execute_skip_small_groups():
    """파일이 2개 미만인 그룹은 스킵 테스트."""
    containment_detector = ContainmentDetector()

    # BlockingGroup 생성 (파일 1개만)
    blocking_group = BlockingGroup(series_title_norm="test", extension=".txt", file_ids=[1])

    stage = RelationDetectionStage(containment_detector=containment_detector)

    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.blocking_groups = [blocking_group]
    context.file_id_mapping = {1: 10}
    context.file_entries_map = {
        10: FileEntry(
            path=Path("test.txt"), size=100, mtime=datetime.now(), extension=".txt", file_id=1
        )
    }

    result_context = stage.execute(context)

    # 파일이 2개 미만이면 결과에 포함되지 않음
    assert len(result_context.results) == 0
