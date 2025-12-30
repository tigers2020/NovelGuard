"""
중복 분석 모듈 테스트

중복 파일 탐지 기능을 테스트합니다.
"""

import sys
import unittest
import tempfile
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.file_record import FileRecord
from analyzers.duplicate_analyzer import DuplicateAnalyzer
from utils.filename_parser import extract_title, extract_normalized_title, extract_episode_range
from utils.text_normalizer import normalize_title, normalize_text_for_comparison
from utils.union_find import UnionFind
from utils.content_comparator import check_range_inclusion


class TestFilenameParser(unittest.TestCase):
    """파일명 파싱 테스트."""
    
    def test_extract_title(self) -> None:
        """제목 추출 테스트."""
        self.assertEqual(
            extract_title("게임 속 최종보스가 되었다 1-114.txt"),
            "게임 속 최종보스가 되었다"
        )
        self.assertEqual(
            extract_title("갓 오브 블랙필드 1부 01권.txt"),
            "갓 오브 블랙필드 1부"
        )
    
    def test_extract_episode_range(self) -> None:
        """회차 범위 추출 테스트."""
        self.assertEqual(
            extract_episode_range("게임 속 최종보스가 되었다 1-114.txt"),
            (1, 114)
        )
        self.assertEqual(
            extract_episode_range("갓 오브 블랙필드 1부 01권.txt"),
            None
        )
    
    def test_extract_normalized_title(self) -> None:
        """정규화 제목 추출 테스트."""
        title = extract_normalized_title("게임 속 최종보스가 되었다 (완결) 1-114.txt")
        self.assertIn("게임 속 최종보스가 되었다", title)
        self.assertNotIn("완결", title)


class TestTextNormalizer(unittest.TestCase):
    """텍스트 정규화 테스트."""
    
    def test_normalize_title(self) -> None:
        """제목 정규화 테스트."""
        self.assertEqual(
            normalize_title("게임 속 최종보스가 되었다 (완결)"),
            "게임 속 최종보스가 되었다"
        )
        self.assertEqual(
            normalize_title("갓  오브   블랙필드"),
            "갓 오브 블랙필드"
        )
    
    def test_normalize_text_for_comparison(self) -> None:
        """본문 비교용 정규화 테스트."""
        text1 = "안녕하세요\r\n반갑습니다  "
        text2 = "안녕하세요\n반갑습니다"
        normalized1 = normalize_text_for_comparison(text1)
        normalized2 = normalize_text_for_comparison(text2)
        self.assertEqual(normalized1, normalized2)


class TestUnionFind(unittest.TestCase):
    """Union-Find 테스트."""
    
    def test_union_find_basic(self) -> None:
        """기본 Union-Find 동작 테스트."""
        uf = UnionFind(5)
        
        # 0, 1, 2를 하나의 그룹으로
        uf.union(0, 1)
        uf.union(1, 2)
        
        # 3, 4를 다른 그룹으로
        uf.union(3, 4)
        
        # 같은 그룹 확인
        self.assertEqual(uf.find(0), uf.find(1))
        self.assertEqual(uf.find(1), uf.find(2))
        self.assertEqual(uf.find(3), uf.find(4))
        
        # 다른 그룹 확인
        self.assertNotEqual(uf.find(0), uf.find(3))
    
    def test_get_groups(self) -> None:
        """그룹 가져오기 테스트."""
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(3, 4)
        
        groups = uf.get_groups()
        self.assertEqual(len(groups), 2)  # 2개 그룹


class TestContentComparator(unittest.TestCase):
    """포함 관계 확인 테스트."""
    
    def test_check_range_inclusion(self) -> None:
        """회차 범위 포함 확인 테스트."""
        self.assertTrue(check_range_inclusion((1, 114), (1, 158)))
        self.assertFalse(check_range_inclusion((1, 158), (1, 114)))
        self.assertFalse(check_range_inclusion((1, 100), (50, 200)))


class TestDuplicateAnalyzer(unittest.TestCase):
    """중복 분석 테스트."""
    
    def setUp(self) -> None:
        """테스트 설정."""
        self.analyzer = DuplicateAnalyzer()
    
    def test_group_by_normalized_title(self) -> None:
        """정규화 제목별 그룹핑 테스트."""
        records = [
            FileRecord(
                path=Path("file1.txt"),
                name="게임 속 최종보스가 되었다 1-114.txt",
                size=1000,
                normalized_title="게임 속 최종보스가 되었다"
            ),
            FileRecord(
                path=Path("file2.txt"),
                name="게임 속 최종보스가 되었다 1-158.txt",
                size=2000,
                normalized_title="게임 속 최종보스가 되었다"
            ),
            FileRecord(
                path=Path("file3.txt"),
                name="갓 오브 블랙필드 1부 01권.txt",
                size=1500,
                normalized_title="갓 오브 블랙필드 1부"
            ),
        ]
        
        groups = self.analyzer._group_by_normalized_title(records)
        self.assertEqual(len(groups), 2)  # 2개 그룹
        self.assertEqual(len(groups["게임 속 최종보스가 되었다"]), 2)
        self.assertEqual(len(groups["갓 오브 블랙필드 1부"]), 1)
    
    def test_analyze_empty_list(self) -> None:
        """빈 리스트 분석 테스트."""
        result = self.analyzer.analyze([])
        self.assertEqual(result, [])
    
    def test_analyze_single_file(self) -> None:
        """단일 파일 분석 테스트."""
        records = [
            FileRecord(
                path=Path("file1.txt"),
                name="test.txt",
                size=1000
            )
        ]
        
        result = self.analyzer.analyze(records)
        self.assertEqual(result, [])  # 중복 없음


if __name__ == "__main__":
    unittest.main()

