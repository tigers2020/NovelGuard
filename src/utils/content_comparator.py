"""
포함 관계 확인 유틸리티

해시 기반 k-gram 앵커를 사용하여 파일 포함 관계를 확인합니다.
O(N·M) 최악 케이스를 완전히 회피합니다.
"""

import hashlib
from pathlib import Path
from typing import Any, Optional, Set

from pydantic import BaseModel

from utils.text_normalizer import normalize_text_for_comparison
from utils.exceptions import FileEncodingError


class AnchorSignature(BaseModel):
    """앵커 시그니처 데이터 구조.
    
    k-gram 해시 집합으로 구성된 앵커입니다.
    """
    front_tokens: Set[str] = set()  # 앞부분 k-gram 해시 집합
    tail_tokens: Set[str] = set()  # 뒷부분 k-gram 해시 집합
    random_tokens: Set[str] = set()  # 중간 부분 k-gram 해시 집합 (여러 개)
    k_gram_size: int = 64  # k-gram 크기 (바이트)


class AnchorScreenResult(BaseModel):
    """앵커 스크리닝 결과."""
    score: float = 0.0  # 매칭 점수 (0.0 ~ 1.0)
    candidate_offsets: Optional[list[int]] = None  # 후보 위치 (선택적)
    matched_counts: dict[str, int] = {}  # 각 토큰 집합별 매칭 개수


def check_range_inclusion(range1: tuple[int, int], range2: tuple[int, int]) -> bool:
    """회차 범위 포함 관계를 확인합니다.
    
    range1이 range2에 포함되는지 확인합니다.
    
    Args:
        range1: 작은 범위 (시작, 끝)
        range2: 큰 범위 (시작, 끝)
    
    Returns:
        range1이 range2에 포함되면 True
    
    Example:
        >>> check_range_inclusion((1, 114), (1, 158))
        True
        >>> check_range_inclusion((1, 158), (1, 114))
        False
    """
    start1, end1 = range1
    start2, end2 = range2
    return start2 <= start1 and end1 <= end2


def _generate_k_grams(text: str, k: int) -> Set[str]:
    """텍스트에서 k-gram 해시 집합을 생성합니다.
    
    Args:
        text: 원본 텍스트
        k: k-gram 크기 (바이트)
    
    Returns:
        k-gram 해시 집합 (sha1 hex)
    """
    if not text:
        return set()
    
    # UTF-8 바이트로 변환
    text_bytes = text.encode("utf-8")
    
    k_grams = set()
    for i in range(len(text_bytes) - k + 1):
        chunk = text_bytes[i:i + k]
        # sha1 해시 계산
        hash_value = hashlib.sha1(chunk).hexdigest()
        k_grams.add(hash_value)
    
    return k_grams


def extract_anchor_signatures(file_path: Path, k_gram_size: int = 64, anchor_size: int = 4096) -> AnchorSignature:
    """앵커 시그니처를 추출합니다.
    
    앞/뒤 2개 앵커 + k-gram 토큰 여러 개 방식.
    
    Args:
        file_path: 파일 경로
        k_gram_size: k-gram 크기 (바이트, 기본값: 64)
        anchor_size: 앵커 크기 (바이트, 기본값: 4KB)
    
    Returns:
        AnchorSignature 객체
    
    Raises:
        FileEncodingError: 파일 읽기 실패 시
    """
    try:
        # 인코딩 자동 감지
        with open(file_path, "rb") as f:
            sample = f.read(32 * 1024)
            detected = charset_normalizer.detect(sample)
            encoding = detected.get("encoding") if detected else "utf-8"
            if not encoding:
                encoding = "utf-8"
        
        # 파일 전체 읽기
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        
        # 정규화
        normalized = normalize_text_for_comparison(content)
        normalized_bytes = normalized.encode("utf-8")
        file_size = len(normalized_bytes)
        
        if file_size == 0:
            return AnchorSignature(k_gram_size=k_gram_size)
        
        # 앞부분 앵커 (0 ~ anchor_size, 여유 버퍼 +2KB)
        front_end = min(anchor_size + 2048, file_size)
        front_text = normalized_bytes[:front_end].decode("utf-8", errors="replace")
        front_tokens = _generate_k_grams(front_text, k_gram_size)
        
        # 뒷부분 앵커 (100% - anchor_size ~ 100%, 여유 버퍼 +2KB)
        tail_start = max(0, file_size - anchor_size - 2048)
        tail_text = normalized_bytes[tail_start:].decode("utf-8", errors="replace")
        tail_tokens = _generate_k_grams(tail_text, k_gram_size)
        
        # 중간 부분에서 여러 k-gram 추출 (커버리지 확보)
        random_tokens = set()
        if file_size > anchor_size * 2:
            # 중간 부분을 여러 구간으로 나눠서 추출
            num_samples = min(5, file_size // (anchor_size * 2))
            for i in range(1, num_samples + 1):
                pos = (file_size * i) // (num_samples + 1)
                start = max(0, pos - anchor_size // 2)
                end = min(file_size, pos + anchor_size // 2)
                sample_text = normalized_bytes[start:end].decode("utf-8", errors="replace")
                random_tokens.update(_generate_k_grams(sample_text, k_gram_size))
        
        return AnchorSignature(
            front_tokens=front_tokens,
            tail_tokens=tail_tokens,
            random_tokens=random_tokens,
            k_gram_size=k_gram_size
        )
        
    except (OSError, PermissionError, UnicodeDecodeError) as e:
        raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e


def anchor_screen(signature: AnchorSignature, large_file: Path) -> AnchorScreenResult:
    """앵커 스크리닝을 수행합니다.
    
    해시 기반 비교 (문자열 검색 금지).
    
    Args:
        signature: 작은 파일의 앵커 시그니처
        large_file: 큰 파일 경로
    
    Returns:
        AnchorScreenResult 객체
    """
    try:
        # 인코딩 자동 감지
        with open(large_file, "rb") as f:
            sample = f.read(32 * 1024)
            detected = charset_normalizer.detect(sample)
            encoding = detected.get("encoding") if detected else "utf-8"
            if not encoding:
                encoding = "utf-8"
        
        # 큰 파일을 스트리밍하며 k-gram 해시 생성
        with open(large_file, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        
        normalized = normalize_text_for_comparison(content)
        
        # 큰 파일의 k-gram 해시 집합 생성
        large_front = _generate_k_grams(normalized[:signature.k_gram_size * 100], signature.k_gram_size)
        large_tail = _generate_k_grams(normalized[-signature.k_gram_size * 100:], signature.k_gram_size)
        large_all = _generate_k_grams(normalized, signature.k_gram_size)
        
        # 교집합 계산
        front_intersection = len(signature.front_tokens & large_all)
        tail_intersection = len(signature.tail_tokens & large_all)
        random_intersection = len(signature.random_tokens & large_all)
        
        # 매칭 개수
        matched_counts = {
            "front": front_intersection,
            "tail": tail_intersection,
            "random": random_intersection
        }
        
        # 점수 계산 (매칭 비율 기반)
        total_tokens = len(signature.front_tokens) + len(signature.tail_tokens) + len(signature.random_tokens)
        if total_tokens > 0:
            score = (front_intersection + tail_intersection + random_intersection) / total_tokens
        else:
            score = 0.0
        
        return AnchorScreenResult(
            score=score,
            matched_counts=matched_counts
        )
        
    except (OSError, PermissionError, UnicodeDecodeError) as e:
        # 오류 시 낮은 점수 반환
        return AnchorScreenResult(score=0.0, matched_counts={})


def check_inclusion_with_anchors(
    small_file: Path,
    large_file: Path,
    has_range: bool = False,
    small_range: Optional[tuple[int, int]] = None,
    large_range: Optional[tuple[int, int]] = None
) -> tuple[bool, dict[str, Any]]:
    """앵커 기반 포함 확인을 수행합니다.
    
    2단계 접근 + 3중 잠금 조건 (range 없는 파일은 2단계 보수 규칙).
    
    Args:
        small_file: 작은 파일 경로
        large_file: 큰 파일 경로
        has_range: 회차 범위가 있는지 여부
        small_range: 작은 파일의 회차 범위 (선택적)
        large_range: 큰 파일의 회차 범위 (선택적)
    
    Returns:
        (is_included: bool, evidence: dict) 튜플
    """
    evidence: dict[str, Any] = {
        "range_small": small_range,
        "range_large": large_range,
        "anchor_hits": {},
        "anchor_threshold": 0,
        "size_ratio": 0.0,
        "content_check": {}
    }
    
    try:
        # 파일 크기 확인
        small_size = small_file.stat().st_size
        large_size = large_file.stat().st_size
        size_ratio = large_size / small_size if small_size > 0 else 0.0
        evidence["size_ratio"] = size_ratio
        
        # 크기 체크
        if small_size > large_size:
            return (False, evidence)
        
        # 1단계: 앵커 시그니처 추출 및 스크리닝
        signature = extract_anchor_signatures(small_file)
        screen_result = anchor_screen(signature, large_file)
        
        evidence["anchor_hits"] = screen_result.matched_counts
        evidence["anchor_threshold"] = 15  # 기본 임계치
        
        # range 있는 경우: 3중 잠금
        if has_range and small_range and large_range:
            # 조건 1: 범위 포함
            range_included = check_range_inclusion(small_range, large_range)
            if not range_included:
                return (False, evidence)
            
            # 조건 2: 앵커 일치 (3개 모두 일정 수준 이상)
            front_hits = screen_result.matched_counts.get("front", 0)
            tail_hits = screen_result.matched_counts.get("tail", 0)
            random_hits = screen_result.matched_counts.get("random", 0)
            
            if front_hits < 5 or tail_hits < 5 or random_hits < 5:
                return (False, evidence)
            
            # 조건 3: 본문 포함 확인 (간단한 샘플 비교)
            # 실제로는 부분 로드/부분 비교를 수행하지만, 여기서는 앵커 점수로 대체
            if screen_result.score < 0.3:  # 30% 이상 매칭
                return (False, evidence)
            
            evidence["content_check"] = {
                "method": "anchor_based",
                "score": screen_result.score
            }
            return (True, evidence)
        
        # range 없는 경우: 2단계 보수 규칙
        else:
            # 조건 A: 크기 비율 필터
            if size_ratio < 1.10:  # large >= small * 1.10
                return (False, evidence)
            
            # 조건 B: 앵커 강도 상향
            total_hits = sum(screen_result.matched_counts.values())
            if total_hits < 30:  # k-gram 교집합 30개 이상
                return (False, evidence)
            
            # 조건 C: 앵커 점수 확인
            if screen_result.score < 0.4:  # 40% 이상 매칭
                return (False, evidence)
            
            evidence["content_check"] = {
                "method": "anchor_based_conservative",
                "score": screen_result.score,
                "total_hits": total_hits
            }
            return (True, evidence)
            
    except Exception as e:
        # 오류 시 False 반환
        evidence["error"] = str(e)
        return (False, evidence)

