"""Evidence Builder Service 테스트."""

from pathlib import Path

from domain.entities.file import File
from domain.value_objects.file_path import FilePath
from domain.value_objects.file_metadata import FileMetadata
from domain.value_objects.file_hash import FileHashInfo
from domain.value_objects.file_id import create_file_id
from domain.services.file_compare import ComparisonDetail, ComparisonResult
from domain.services.evidence_builder import EvidenceBuilderService


def create_test_file(
    file_id: int,
    name: str = "test.txt",
    hash_strong: str | None = None,
    fingerprint_fast: str | None = None,
    fingerprint_norm: str | None = None,
    simhash64: int | None = None
) -> File:
    """테스트용 File 생성."""
    path = FilePath(
        path=Path(f"/test/{name}"),
        name=name,
        ext=".txt",
        size=1000,
        mtime=1000.0
    )
    metadata = FileMetadata.text_file(encoding="utf-8", confidence=0.95)
    hash_info = FileHashInfo(
        hash_strong=hash_strong,
        fingerprint_fast=fingerprint_fast,
        fingerprint_norm=fingerprint_norm,
        simhash64=simhash64
    )
    
    return File(
        file_id=create_file_id(file_id),
        path=path,
        metadata=metadata,
        hash_info=hash_info
    )


class TestEvidenceBuilderService:
    """EvidenceBuilderService 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = EvidenceBuilderService()
        self.counter = iter(range(1, 1000))
        self.evidence_id_gen = lambda: next(self.counter)
    
    def test_build_hash_strong_evidence(self):
        """강한 해시 증거 생성."""
        file1 = create_test_file(1, "file1.txt", hash_strong="abc123")
        file2 = create_test_file(2, "file2.txt", hash_strong="abc123")
        
        detail = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="strong_hash"
        )
        
        evidence = self.service.build_from_comparison(
            file1, file2, detail, self.evidence_id_gen
        )
        
        assert evidence.evidence_id == 1
        assert evidence.kind == "HASH_STRONG"
        assert evidence.detail["file_id_1"] == 1
        assert evidence.detail["file_id_2"] == 2
        assert evidence.detail["similarity"] == 1.0
        assert evidence.detail["hash_value"] == "abc123"
    
    def test_build_fingerprint_fast_evidence(self):
        """빠른 지문 증거 생성."""
        file1 = create_test_file(1, "file1.txt", fingerprint_fast="fp123")
        file2 = create_test_file(2, "file2.txt", fingerprint_fast="fp123")
        
        detail = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="fingerprint"
        )
        
        evidence = self.service.build_from_comparison(
            file1, file2, detail, self.evidence_id_gen
        )
        
        assert evidence.kind == "FP_FAST"
        assert evidence.detail["fingerprint"] == "fp123"
    
    def test_build_fingerprint_norm_evidence(self):
        """정규화 지문 증거 생성."""
        file1 = create_test_file(1, "file1.txt", fingerprint_norm="norm123")
        file2 = create_test_file(2, "file2.txt", fingerprint_norm="norm123")
        
        detail = ComparisonDetail(
            result=ComparisonResult.SIMILAR,
            similarity_score=1.0,
            matched_by="fingerprint_norm"
        )
        
        evidence = self.service.build_from_comparison(
            file1, file2, detail, self.evidence_id_gen
        )
        
        assert evidence.kind == "NORM_HASH"
        assert evidence.detail["fingerprint"] == "norm123"
    
    def test_build_simhash_evidence(self):
        """SimHash 증거 생성."""
        file1 = create_test_file(1, "file1.txt", simhash64=123456)
        file2 = create_test_file(2, "file2.txt", simhash64=123460)
        
        detail = ComparisonDetail(
            result=ComparisonResult.SIMILAR,
            similarity_score=0.93,
            matched_by="simhash"
        )
        
        evidence = self.service.build_from_comparison(
            file1, file2, detail, self.evidence_id_gen
        )
        
        assert evidence.kind == "SIMHASH"
        assert evidence.detail["similarity"] == 0.93
        assert evidence.detail["simhash_1"] == 123456
        assert evidence.detail["simhash_2"] == 123460
    
    def test_evidence_id_generation(self):
        """증거 ID가 순차적으로 생성되는지 확인."""
        file1 = create_test_file(1, "file1.txt", hash_strong="abc")
        file2 = create_test_file(2, "file2.txt", hash_strong="abc")
        file3 = create_test_file(3, "file3.txt", hash_strong="def")
        file4 = create_test_file(4, "file4.txt", hash_strong="def")
        
        detail1 = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="strong_hash"
        )
        detail2 = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="strong_hash"
        )
        
        evidence1 = self.service.build_from_comparison(
            file1, file2, detail1, self.evidence_id_gen
        )
        evidence2 = self.service.build_from_comparison(
            file3, file4, detail2, self.evidence_id_gen
        )
        
        assert evidence1.evidence_id == 1
        assert evidence2.evidence_id == 2
    
    def test_build_encoding_evidence(self):
        """인코딩 문제 증거 생성."""
        file = create_test_file(1, "file.txt")
        
        evidence = self.service.build_encoding_evidence(
            file,
            self.evidence_id_gen,
            issue_description="인코딩 감지 실패"
        )
        
        assert evidence.evidence_id == 1
        assert evidence.detail["file_id"] == 1
        assert evidence.detail["encoding"] == "utf-8"
        assert evidence.detail["description"] == "인코딩 감지 실패"
    
    def test_build_multiple_evidences(self):
        """여러 증거 동시 생성."""
        file1 = create_test_file(1, "file1.txt", hash_strong="abc")
        file2 = create_test_file(2, "file2.txt", hash_strong="abc")
        file3 = create_test_file(3, "file3.txt", hash_strong="def")
        file4 = create_test_file(4, "file4.txt", hash_strong="def")
        
        comparisons = [
            (file1, file2, ComparisonDetail(ComparisonResult.IDENTICAL, 1.0, "strong_hash")),
            (file3, file4, ComparisonDetail(ComparisonResult.IDENTICAL, 1.0, "strong_hash")),
        ]
        
        evidences = self.service.build_multiple_evidences(
            comparisons, self.evidence_id_gen
        )
        
        assert len(evidences) == 2
        assert evidences[0].evidence_id == 1
        assert evidences[1].evidence_id == 2
        assert all(e.kind == "HASH_STRONG" for e in evidences)


class TestEvidenceBuilderKindDetermination:
    """EvidenceBuilderService 종류 결정 테스트."""
    
    def setup_method(self):
        """각 테스트 전 실행."""
        self.service = EvidenceBuilderService()
    
    def test_determine_kind_hash_strong(self):
        """HASH_STRONG 결정."""
        detail = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="strong_hash"
        )
        
        kind = self.service._determine_kind(detail)
        assert kind == "HASH_STRONG"
    
    def test_determine_kind_fp_fast(self):
        """FP_FAST 결정."""
        detail = ComparisonDetail(
            result=ComparisonResult.IDENTICAL,
            similarity_score=1.0,
            matched_by="fingerprint"
        )
        
        kind = self.service._determine_kind(detail)
        assert kind == "FP_FAST"
    
    def test_determine_kind_norm_hash(self):
        """NORM_HASH 결정."""
        detail = ComparisonDetail(
            result=ComparisonResult.SIMILAR,
            similarity_score=1.0,
            matched_by="fingerprint_norm"
        )
        
        kind = self.service._determine_kind(detail)
        assert kind == "NORM_HASH"
    
    def test_determine_kind_simhash(self):
        """SIMHASH 결정."""
        detail = ComparisonDetail(
            result=ComparisonResult.SIMILAR,
            similarity_score=0.93,
            matched_by="simhash"
        )
        
        kind = self.service._determine_kind(detail)
        assert kind == "SIMHASH"
    
    def test_determine_kind_unknown(self):
        """알 수 없는 방법은 기본값."""
        detail = ComparisonDetail(
            result=ComparisonResult.DIFFERENT,
            similarity_score=0.0,
            matched_by=None
        )
        
        kind = self.service._determine_kind(detail)
        assert kind == "HASH_STRONG"  # 기본값
