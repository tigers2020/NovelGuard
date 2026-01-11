"""Integrity Check Service 테스트."""

from pathlib import Path

from domain.entities.file import File
from domain.value_objects.file_path import FilePath
from domain.value_objects.file_metadata import FileMetadata
from domain.value_objects.file_hash import FileHashInfo
from domain.value_objects.file_id import create_file_id
from domain.services.integrity_checker import IntegrityCheckService


def create_test_file(
    file_id: int,
    name: str = "test.txt",
    size: int = 1000,
    is_text: bool = True,
    encoding: str | None = "utf-8",
    confidence: float | None = 0.95
) -> File:
    """테스트용 File 생성."""
    path = FilePath(
        path=Path(f"/test/{name}"),
        name=name,
        ext=".txt" if is_text else ".bin",
        size=size,
        mtime=1000.0
    )
    
    # 인코딩이 명시적으로 None이면 is_text=True로 강제
    # (텍스트 파일이지만 인코딩 미감지 상황)
    if encoding is None and is_text:
        metadata = FileMetadata(
            is_text=True,
            encoding_detected=None,
            encoding_confidence=None,
            newline=None
        )
    elif is_text and encoding:
        metadata = FileMetadata.text_file(
            encoding=encoding,
            confidence=confidence
        )
    else:
        metadata = FileMetadata.binary_file()
    
    return File(
        file_id=create_file_id(file_id),
        path=path,
        metadata=metadata,
        hash_info=FileHashInfo()
    )


class TestIntegrityCheckService:
    """IntegrityCheckService 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = IntegrityCheckService()
        self.counter = iter(range(1, 1000))
        self.issue_id_gen = lambda: next(self.counter)
    
    def test_check_normal_file(self):
        """정상 파일은 이슈 없음."""
        file = create_test_file(
            file_id=1,
            name="normal.txt",
            size=1000,
            encoding="utf-8",
            confidence=0.95
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 0
    
    def test_check_empty_file(self):
        """빈 파일은 INFO 이슈."""
        file = create_test_file(
            file_id=1,
            name="empty.txt",
            size=0,  # 빈 파일
            encoding="utf-8",
            confidence=0.95
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 1
        
        issue = issues[0]
        assert issue.category == "EMPTY"
        assert issue.severity == "INFO"
        assert issue.fixable is False
    
    def test_check_no_encoding(self):
        """인코딩 정보 없으면 ERROR."""
        file = create_test_file(
            file_id=1,
            name="unknown.txt",
            size=1000,
            encoding=None,  # 인코딩 없음
            confidence=None
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 1
        
        issue = issues[0]
        assert issue.category == "ENCODING"
        assert issue.severity == "ERROR"
        assert issue.fixable is False
    
    def test_check_low_confidence_error(self):
        """낮은 신뢰도 (< 0.5) → ERROR."""
        file = create_test_file(
            file_id=1,
            name="low_conf.txt",
            size=1000,
            encoding="utf-8",
            confidence=0.3  # 매우 낮음
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 1
        
        issue = issues[0]
        assert issue.category == "ENCODING"
        assert issue.severity == "ERROR"
        assert issue.fixable is True
        assert issue.suggested_fix == "CONVERT_UTF8"
    
    def test_check_low_confidence_warn(self):
        """낮은 신뢰도 (0.5 ~ 0.7) → WARN."""
        file = create_test_file(
            file_id=1,
            name="medium_conf.txt",
            size=1000,
            encoding="utf-8",
            confidence=0.6  # 중간
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 1
        
        issue = issues[0]
        assert issue.category == "ENCODING"
        assert issue.severity == "WARN"
        assert issue.fixable is False
    
    def test_check_binary_file_no_encoding_check(self):
        """바이너리 파일은 인코딩 체크 안 함."""
        file = create_test_file(
            file_id=1,
            name="image.bin",
            size=1000,
            is_text=False  # 바이너리
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 0  # 인코딩 체크 안 함
    
    def test_check_multiple_issues(self):
        """여러 이슈 발견."""
        file = create_test_file(
            file_id=1,
            name="empty.txt",
            size=0,  # 빈 파일 (INFO)
            encoding=None,  # 인코딩 없음 (ERROR)
            confidence=None
        )
        
        issues = self.service.check_file(file, self.issue_id_gen)
        assert len(issues) == 2  # EMPTY + ENCODING
        
        # 이슈 ID가 다름
        assert issues[0].issue_id != issues[1].issue_id


class TestIntegrityCheckServiceMultiple:
    """IntegrityCheckService 다중 파일 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = IntegrityCheckService()
        self.counter = iter(range(1, 1000))
        self.issue_id_gen = lambda: next(self.counter)
    
    def test_check_multiple_files(self):
        """여러 파일 동시 검사."""
        files = [
            create_test_file(1, "normal.txt", size=1000),  # 정상
            create_test_file(2, "empty.txt", size=0),  # 빈 파일
            create_test_file(3, "low.txt", confidence=0.3),  # 낮은 신뢰도
        ]
        
        results = self.service.check_multiple_files(files, self.issue_id_gen)
        
        # file 1은 이슈 없음 (결과에 포함 안 됨)
        assert create_file_id(1) not in results
        
        # file 2는 이슈 있음
        assert create_file_id(2) in results
        assert len(results[create_file_id(2)]) == 1
        assert results[create_file_id(2)][0].category == "EMPTY"
        
        # file 3은 이슈 있음
        assert create_file_id(3) in results
        assert len(results[create_file_id(3)]) == 1
        assert results[create_file_id(3)][0].category == "ENCODING"
    
    def test_check_multiple_files_all_normal(self):
        """모두 정상이면 빈 dict."""
        files = [
            create_test_file(1, "file1.txt"),
            create_test_file(2, "file2.txt"),
        ]
        
        results = self.service.check_multiple_files(files, self.issue_id_gen)
        assert results == {}


class TestIntegrityCheckServiceSummary:
    """IntegrityCheckService 요약 통계 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = IntegrityCheckService()
        self.counter = iter(range(1, 1000))
        self.issue_id_gen = lambda: next(self.counter)
    
    def test_get_issue_summary_empty(self):
        """이슈 없으면 빈 통계."""
        summary = self.service.get_issue_summary([])
        
        assert summary['total'] == 0
        assert summary['by_severity'] == {}
        assert summary['by_category'] == {}
        assert summary['fixable_count'] == 0
    
    def test_get_issue_summary_single(self):
        """이슈 하나."""
        files = [create_test_file(1, "empty.txt", size=0)]
        issues = []
        for file in files:
            issues.extend(self.service.check_file(file, self.issue_id_gen))
        
        summary = self.service.get_issue_summary(issues)
        
        assert summary['total'] == 1
        assert summary['by_severity'] == {'INFO': 1}
        assert summary['by_category'] == {'EMPTY': 1}
        assert summary['fixable_count'] == 0
    
    def test_get_issue_summary_multiple(self):
        """여러 이슈."""
        files = [
            create_test_file(1, "empty.txt", size=0),  # INFO
            create_test_file(2, "low1.txt", confidence=0.3),  # ERROR, fixable
            create_test_file(3, "low2.txt", confidence=0.6),  # WARN
            create_test_file(4, "low3.txt", confidence=0.4),  # ERROR, fixable
        ]
        
        issues = []
        for file in files:
            issues.extend(self.service.check_file(file, self.issue_id_gen))
        
        summary = self.service.get_issue_summary(issues)
        
        assert summary['total'] == 4
        assert summary['by_severity'] == {'INFO': 1, 'ERROR': 2, 'WARN': 1}
        assert summary['by_category'] == {'EMPTY': 1, 'ENCODING': 3}
        assert summary['fixable_count'] == 2  # ERROR 2개만 fixable


class TestIntegrityCheckServiceIssueIdGenerator:
    """IntegrityCheckService 이슈 ID 생성 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = IntegrityCheckService()
    
    def test_issue_id_incremental(self):
        """이슈 ID가 증가하는지 확인."""
        counter = iter(range(1, 1000))
        issue_id_gen = lambda: next(counter)
        
        files = [
            create_test_file(1, "empty1.txt", size=0),
            create_test_file(2, "empty2.txt", size=0),
            create_test_file(3, "empty3.txt", size=0),
        ]
        
        issues = []
        for file in files:
            issues.extend(self.service.check_file(file, issue_id_gen))
        
        # ID가 순차적으로 증가
        assert len(issues) == 3
        assert issues[0].issue_id == 1
        assert issues[1].issue_id == 2
        assert issues[2].issue_id == 3
