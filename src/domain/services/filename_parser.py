"""파일명 파싱 서비스."""

import re
from pathlib import Path
from typing import Optional

from domain.value_objects.filename_parse_result import FilenameParseResult
from domain.value_objects.range_segment import RangeSegment


class FilenameParser:
    """파일명 파싱 서비스.

    파일명에서 작품명, 범위, 태그를 추출하는 도메인 서비스.
    중복 탐지의 핵심 데이터를 생성함.
    """

    # 정규식 패턴 정의
    # 패턴 1: "작품명 1-170" 형식
    PATTERN_RANGE_HYPHEN = re.compile(
        r"^(.+?)\s+(\d+)\s*-\s*(\d+)(?:([화권장회])|\(([^)]+)\))?(.*)$"
    )

    # 패턴 2: "작품명 1~170" 형식
    PATTERN_RANGE_TILDE = re.compile(
        r"^(.+?)\s+(\d+)\s*~\s*(\d+)(?:([화권장회])|\(([^)]+)\))?(.*)$"
    )

    # 패턴 3: "작품명 1권" 형식 (단일 범위)
    PATTERN_SINGLE_RANGE = re.compile(r"^(.+?)\s+(\d+)([화권장회부])(.*)$")

    # 패턴 4: "작품명 본편 1-1213 외전 1-71" 형식 (복합 세그먼트)
    # 한 덩어리 정규식은 Sonar S5843(복잡도) 한도를 넘기므로, 첫 세그먼트 / 이후 꼬리를 분리한다.
    _MULTI_SEGMENT_LABEL = r"(본편|외전|에필|후기|1부|2부|3부|4부)"
    PATTERN_MULTI_SEGMENT_HEAD = re.compile(
        rf"^(.+?)\s+{_MULTI_SEGMENT_LABEL}\s+(\d+)\s*-\s*(\d+)",
        re.IGNORECASE,
    )
    PATTERN_MULTI_SEGMENT_CONT = re.compile(
        rf"^\s+{_MULTI_SEGMENT_LABEL}\s+(\d+)\s*-\s*(\d+)(.*)$",
        re.IGNORECASE,
    )

    # 태그 패턴: (완), (完), [에필], @컵라면 등
    PATTERN_TAGS = re.compile(
        r"\(([^)]+)\)|\[([^\]]+)\]|@([^\s]+)|(완결|완전판|완본|후기|에필|에필로그)", re.IGNORECASE
    )

    # 완결 태그
    COMPLETE_TAGS = {"완", "完", "완결", "완전판", "완본", "complete", "finished", "end"}

    # 후기 태그
    EPILOGUE_TAGS = {"후기", "에필", "에필로그", "epilogue", "afterword"}

    def parse(self, path: Path) -> FilenameParseResult:
        """파일명을 파싱하여 FilenameParseResult 반환.

        Args:
            path: 파일 경로.

        Returns:
            파일명 파싱 결과. 파싱 실패 시 기본값 반환 (에러 발생하지 않음).
        """
        filename = path.stem  # 확장자 제거

        # 정규식 패턴 매칭 시도
        result = self._parse_with_patterns(filename, path)
        if result.confidence >= 0.7:
            return result

        # 휴리스틱 파싱 시도
        result = self._parse_with_heuristics(filename, path)
        if result.confidence >= 0.4:
            return result

        # 폴백: 작품명만 추출
        result = self._parse_fallback(filename, path)
        return result

    def _parse_with_patterns(self, filename: str, path: Path) -> FilenameParseResult:
        """정규식 패턴으로 파싱."""
        for try_pattern in (
            self._try_parse_multi_segment_pattern,
            self._try_parse_range_hyphen,
            self._try_parse_range_tilde,
            self._try_parse_single_volume,
        ):
            hit = try_pattern(filename, path)
            if hit is not None:
                return hit
        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=filename.lower(),
            segments=[],
            confidence=0.0,
            parse_method="pattern_match",
        )

    def _multi_segment_continuation(
        self, tail: str
    ) -> tuple[Optional[str], Optional[int], Optional[int], str]:
        """복합 세그먼트 꼬리에서 두 번째 구간과 잔여 문자열을 파싱."""
        cont = self.PATTERN_MULTI_SEGMENT_CONT.match(tail)
        if cont:
            rest = cont.group(4)
            return (
                cont.group(1).strip(),
                int(cont.group(2)),
                int(cont.group(3)),
                rest if rest else "",
            )
        return None, None, None, tail

    def _try_parse_multi_segment_pattern(
        self, filename: str, path: Path
    ) -> Optional[FilenameParseResult]:
        """패턴 4: 작품명 본편 1-1213 외전 1-71 형식 (복합 세그먼트, 우선)."""
        head = self.PATTERN_MULTI_SEGMENT_HEAD.match(filename)
        if not head:
            return None
        series_title = head.group(1).strip()
        segment1_type = head.group(2).strip()
        segment1_start = int(head.group(3))
        segment1_end = int(head.group(4))
        tail = filename[head.end() :]
        seg2_type, seg2_start, seg2_end, remaining = self._multi_segment_continuation(tail)

        series_title_norm = self._normalize_series_title(series_title)
        tags = self._extract_tags(remaining)
        segments = [
            RangeSegment(
                start=segment1_start, end=segment1_end, segment_type=segment1_type, unit=None
            )
        ]
        if seg2_type and seg2_start is not None and seg2_end is not None:
            segments.append(
                RangeSegment(
                    start=seg2_start,
                    end=seg2_end,
                    segment_type=seg2_type,
                    unit=None,
                )
            )
        primary = segments[0]
        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=series_title_norm,
            range_start=primary.start,
            range_end=primary.end,
            range_unit=primary.unit,
            segments=segments,
            tags=tags,
            confidence=0.95,
            parse_method="pattern_match",
        )

    def _parse_result_from_range_delim_match(
        self,
        match: re.Match[str],
        path: Path,
        filename: str,
        confidence: float,
    ) -> FilenameParseResult:
        """하이픈/물결 범위 패턴(그룹 구조 동일) 공통 결과 생성."""
        series_title = match.group(1).strip()
        range_start = int(match.group(2))
        range_end = int(match.group(3))
        unit_g = match.group(4)
        range_unit = unit_g if unit_g else None
        tag_g = match.group(5)
        tag_content = tag_g if tag_g else ""
        rem_g = match.group(6)
        remaining = rem_g if rem_g else ""

        series_title_norm = self._normalize_series_title(series_title)
        tags = self._extract_tags(tag_content + remaining)
        segments = [
            RangeSegment(
                start=range_start,
                end=range_end,
                segment_type=None,
                unit=range_unit,
            )
        ]
        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=series_title_norm,
            range_start=range_start,
            range_end=range_end,
            range_unit=range_unit,
            segments=segments,
            tags=tags,
            confidence=confidence,
            parse_method="pattern_match",
        )

    def _try_parse_range_hyphen(self, filename: str, path: Path) -> Optional[FilenameParseResult]:
        """패턴 1: 작품명 1-170 형식."""
        m = self.PATTERN_RANGE_HYPHEN.match(filename)
        if not m:
            return None
        return self._parse_result_from_range_delim_match(m, path, filename, 0.9)

    def _try_parse_range_tilde(self, filename: str, path: Path) -> Optional[FilenameParseResult]:
        """패턴 2: 작품명 1~170 형식."""
        m = self.PATTERN_RANGE_TILDE.match(filename)
        if not m:
            return None
        return self._parse_result_from_range_delim_match(m, path, filename, 0.85)

    def _try_parse_single_volume(self, filename: str, path: Path) -> Optional[FilenameParseResult]:
        """패턴 3: 작품명 1권 형식."""
        match = self.PATTERN_SINGLE_RANGE.match(filename)
        if not match:
            return None
        series_title = match.group(1).strip()
        range_num = int(match.group(2))
        range_unit = match.group(3)
        rem_g = match.group(4)
        remaining = rem_g if rem_g else ""

        series_title_norm = self._normalize_series_title(series_title)
        tags = self._extract_tags(remaining)
        segments = [
            RangeSegment(
                segment_type=None,
                start=range_num,
                end=range_num,
                unit=range_unit,
            )
        ]
        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=series_title_norm,
            range_start=range_num,
            range_end=range_num,
            range_unit=range_unit,
            segments=segments,
            tags=tags,
            confidence=0.8,
            parse_method="pattern_match",
        )

    def _parse_with_heuristics(self, filename: str, path: Path) -> FilenameParseResult:
        """휴리스틱으로 파싱."""
        # 숫자 범위 찾기 (예: "1-170", "0-59")
        range_match = re.search(r"(\d+)\s*[-~]\s*(\d+)", filename)
        if range_match:
            range_start = int(range_match.group(1))
            range_end = int(range_match.group(2))

            # 범위 앞부분을 작품명으로 추정
            series_part = filename[: range_match.start()].strip()
            if series_part:
                series_title_norm = self._normalize_series_title(series_part)
            else:
                series_title_norm = filename.lower()

            tags = self._extract_tags(filename)

            # segments 생성 (primary segment만)
            segments = [
                RangeSegment(
                    segment_type=None,  # primary segment
                    start=range_start,
                    end=range_end,
                    unit=None,
                )
            ]

            return FilenameParseResult(
                original_path=path,
                original_name=filename,
                series_title_norm=series_title_norm,
                range_start=range_start,
                range_end=range_end,
                segments=segments,
                tags=tags,
                confidence=0.5,
                parse_method="heuristic",
            )

        # 휴리스틱 실패
        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=filename.lower(),
            segments=[],
            confidence=0.0,
            parse_method="heuristic",
        )

    def _parse_fallback(self, filename: str, path: Path) -> FilenameParseResult:
        """폴백 파싱 (작품명만 추출)."""
        # 태그 제거 시도
        cleaned = re.sub(r"[\(\[][^\)\]]*[\)\]]", "", filename)  # (태그), [태그] 제거
        cleaned = re.sub(r"@[^\s]+", "", cleaned)  # @태그 제거
        cleaned = cleaned.strip()

        series_title_norm = self._normalize_series_title(cleaned if cleaned else filename)
        tags = self._extract_tags(filename)

        return FilenameParseResult(
            original_path=path,
            original_name=filename,
            series_title_norm=series_title_norm,
            segments=[],
            tags=tags,
            confidence=0.2,
            parse_method="fallback",
        )

    def _normalize_series_title(self, title: str) -> str:
        """작품명 정규화.

        Args:
            title: 원본 작품명.

        Returns:
            정규화된 작품명 (소문자, 공백 정리, 태그 제거).
        """
        # 태그 제거
        normalized = re.sub(r"[\(\[][^\)\]]*[\)\]]", "", title)  # (태그), [태그] 제거
        normalized = re.sub(r"@[^\s]+", "", normalized)  # @태그 제거

        # 완결 태그 단어 기반 제거 (문자 클래스가 아닌 alternation 사용)
        # 주의: [완결完후기에필]+ 같은 문자 클래스는 개별 문자를 삭제하므로
        # 서로 다른 작품명이 같은 normalized로 뭉개질 수 있음
        tag_words_pattern = re.compile(
            r"(완결|완전판|완본|완|完|후기|에필로그|에필|epilogue|afterword|complete|finished|end)",
            re.IGNORECASE,
        )
        normalized = tag_words_pattern.sub("", normalized)

        # 공백 정리
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 소문자 변환 (한글은 영향 없음)
        normalized = normalized.lower()

        return normalized

    def _extract_tags(self, text: str) -> list[str]:
        """태그 추출.

        Args:
            text: 태그가 포함된 텍스트.

        Returns:
            태그 리스트.
        """
        tags = []

        # 정규식으로 태그 찾기
        for match in self.PATTERN_TAGS.finditer(text):
            # 그룹 1: (태그)
            if match.group(1):
                tags.append(match.group(1))
            # 그룹 2: [태그]
            elif match.group(2):
                tags.append(match.group(2))
            # 그룹 3: @태그
            elif match.group(3):
                tags.append(match.group(3))
            # 그룹 4: 단독 태그 (완결, 후기 등)
            elif match.group(4):
                tags.append(match.group(4))

        # 중복 제거 및 정리
        unique_tags = []
        seen = set()
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                unique_tags.append(tag)
                seen.add(tag_lower)

        return unique_tags
