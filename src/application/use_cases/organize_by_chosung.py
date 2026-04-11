"""초성별 폴더 정리 UseCase.

대상 폴더 및 하위 폴더의 모든 파일을 제목 첫 글자(초성/A-Z/0-9)에 따라
ㄱ-ㄷ, ㄹ-ㅂ, ㅅ-ㅈ, ㅊ-ㅎ, A-Z, 0-9, 기타 폴더로 분류해 이동/복사합니다.
파일명 앞의 [...] (...) 는 제거한 뒤의 제목으로 분류합니다.
"""
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step

# 정리 결과를 넣을 한 단계 하위 폴더명 (같은 루트에 섞이지 않도록)
OUTPUT_SUBFOLDER = "정리"

# 19개 초성 (유니코드 한글 초성 순서)
_CHOSUNG_19 = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
# 19개 초성 → 14개 기본 자음 인덱스 (ㄲ→ㄱ, ㄸ→ㄷ, ㅃ→ㅂ, ㅆ→ㅅ, ㅉ→ㅈ)
_CHOSUNG_TO_BASIC_INDEX = (0, 0, 1, 2, 2, 3, 4, 5, 5, 6, 6, 7, 8, 8, 9, 10, 11, 12, 13)
# 14개 기본 자음 → 구간 인덱스 (ㄱㄴㄷ→0, ㄹㅁㅂ→1, ㅅㅇㅈ→2, ㅊㅋㅌㅍㅎ→3)
_BASIC_INDEX_TO_GROUP = (0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3)
# 구간 폴더명: ㄱ-ㄷ, ㄹ-ㅂ, ㅅ-ㅈ, ㅊ-ㅎ + A-Z, 0-9, 기타 = 7개
FOLDER_NAMES = (
    ("ㄱ-ㄷ", "ㄹ-ㅂ", "ㅅ-ㅈ", "ㅊ-ㅎ")
    + ("A-Z", "0-9", "기타")
)


# 앞쪽 [...] / (...) 블록을 한 번에 제거하는 정규식 (반복 매칭)
_STRIP_LEADING_BRACKETS = re.compile(r"^(\s*(\[[^\]]*\]|\([^)]*\))\s*)+")


def effective_stem_for_sort(stem: str) -> str:
    """파일명(확장자 제외)에서 앞의 [...] (...) 를 제거한 제목 부분 반환."""
    s = stem.strip()
    return _STRIP_LEADING_BRACKETS.sub("", s).strip()


def get_chosung_folder_name(first_char: str) -> str:
    """문자 하나에서 분류 폴더명 반환: 한글→ㄱ-ㄷ/ㄹ-ㅂ/ㅅ-ㅈ/ㅊ-ㅎ, 영문→A-Z, 숫자→0-9, 그 외 기타."""
    if not first_char:
        return "기타"
    c = first_char
    code = ord(c)
    if 0xAC00 <= code <= 0xD7A3:
        syllable_index = code - 0xAC00
        chosung_index = syllable_index // 588
        basic_index = _CHOSUNG_TO_BASIC_INDEX[chosung_index]
        group_index = _BASIC_INDEX_TO_GROUP[basic_index]
        return FOLDER_NAMES[group_index]
    if "A" <= c <= "Z" or "a" <= c <= "z":
        return "A-Z"
    if "0" <= c <= "9":
        return "0-9"
    return "기타"


def normalize_target_filename(name: str) -> str:
    """파일명에서 끝의 ' (1)', ' (2)', ' (1).' 등 제거한 이름 반환."""
    if not name:
        return name
    stem, suffix = (name.rsplit(".", 1) + [""])[:2]
    if suffix:
        suffix = "." + suffix
    # stem 끝이 " (숫자)" 또는 " (숫자)." 이면 제거
    match = re.match(r"^(.+?) \(\d+\)\.?$", stem)
    if match:
        stem = match.group(1)
    return stem + suffix


@dataclass
class OrganizeByChosungResult:
    """초성별 정리 결과."""

    total_processed: int = 0
    """처리한 파일 수."""
    moved_or_copied: int = 0
    """실제 이동/복사된 파일 수."""
    skipped: int = 0
    """건너뛴 파일 수 (같은 이름 등)."""
    counts_by_folder: dict[str, int] = field(default_factory=dict)
    """폴더별 이동/복사된 파일 수."""
    files_already_in_chosung: int = 0
    """이미 초성 구간(ㄱ-ㄷ 등)·기타 폴더 안에 있어서 제외된 파일 수 (정리할 파일이 0일 때 참고용)."""


class OrganizeByChosungUseCase:
    """초성별 폴더 정리 UseCase.

    대상 폴더 및 하위 폴더의 모든 파일을 파일명 첫 글자 초성에 따라
    ㄱ-ㄷ, ㄹ-ㅂ, ㅅ-ㅈ, ㅊ-ㅎ, A-Z, 0-9, 기타 폴더 바로 아래로 이동/복사합니다 (하위 폴더 없음).
    """

    def __init__(self, log_sink: Optional[ILogSink] = None) -> None:
        self._log_sink = log_sink

    def _collect_all_files_recursive(self, root_path: Path) -> list[Path]:
        """루트 아래 모든 파일을 재귀 수집. 출력 폴더(정리) 안은 제외."""
        collected: list[Path] = []
        for path in root_path.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root_path)
            except ValueError:
                continue
            if rel.parts and rel.parts[0] == OUTPUT_SUBFOLDER:
                continue
            collected.append(path)
        return collected

    def _first_char_for_folder(self, path: Path) -> str:
        """파일 경로에서 분류용 첫 글자 반환 (앞의 [] () 제거 후)."""
        stem = effective_stem_for_sort(path.stem) if path.stem else ""
        return stem[:1] if stem else ""

    def _apply_dry_run(
        self, files: list[Path], result: OrganizeByChosungResult
    ) -> OrganizeByChosungResult:
        """dry_run: 폴더별 개수만 계산."""
        for path in files:
            first_char = self._first_char_for_folder(path)
            folder_name = get_chosung_folder_name(first_char)
            result.counts_by_folder[folder_name] = result.counts_by_folder.get(folder_name, 0) + 1
            result.total_processed += 1
            result.moved_or_copied += 1
        debug_step(
            self._log_sink,
            "organize_by_chosung_dry_run",
            {"total": result.total_processed, "counts": result.counts_by_folder},
        )
        return result

    def _unique_flat_path(self, dir_path: Path, name: str) -> Path:
        """같은 디렉터리 내에서 사용 가능한 파일 경로 반환 (이름 충돌 시 번호 부여)."""
        target = dir_path / name
        if not target.exists():
            return target
        stem, suffix = (target.stem, target.suffix)
        if suffix:
            suffix = "." + suffix
        n = 1
        while True:
            candidate = dir_path / f"{stem} ({n}){suffix}"
            if not candidate.exists():
                return candidate
            n += 1

    def _apply_move_or_copy(
        self,
        target_base: Path,
        files: list[Path],
        move: bool,
        result: OrganizeByChosungResult,
    ) -> None:
        """target_base(정리) 아래 초성 폴더 생성 후 파일 이동/복사. 파일명 끝 ' (1)' 등은 제거한 이름 사용."""
        target_base.mkdir(parents=True, exist_ok=True)
        for name in FOLDER_NAMES:
            (target_base / name).mkdir(parents=False, exist_ok=True)
        for path in files:
            first_char = self._first_char_for_folder(path)
            folder_name = get_chosung_folder_name(first_char)
            target_dir = target_base / folder_name
            target_name = normalize_target_filename(path.name)
            target_path = self._unique_flat_path(target_dir, target_name)
            if target_path.resolve() == path.resolve():
                result.total_processed += 1
                result.moved_or_copied += 1
                result.counts_by_folder[folder_name] = result.counts_by_folder.get(folder_name, 0) + 1
                continue
            try:
                if move:
                    shutil.move(str(path), str(target_path))
                else:
                    shutil.copy2(str(path), str(target_path))
                result.counts_by_folder[folder_name] = result.counts_by_folder.get(folder_name, 0) + 1
                result.moved_or_copied += 1
            except OSError:
                result.skipped += 1
            result.total_processed += 1

    def _count_files_in_output(self, target_base: Path) -> int:
        """출력 폴더(정리) 아래 초성 폴더들에 있는 파일 수. 한 번의 트리 순회로 계산."""
        if not target_base.is_dir():
            return 0
        return sum(1 for p in target_base.rglob("*") if p.is_file())

    def _is_dir_candidate_for_removal(self, root_path: Path, path: Path) -> bool:
        """경로가 빈 폴더 삭제 후보인지 여부. 출력 폴더(정리) 및 그 직하위 초성 폴더는 제외."""
        if not path.is_dir():
            return False
        try:
            rel = path.relative_to(root_path)
        except ValueError:
            return False
        if not rel.parts:
            return False
        if rel.parts[0] != OUTPUT_SUBFOLDER:
            return True
        if len(rel.parts) == 1:
            return False
        if len(rel.parts) == 2 and rel.parts[1] in FOLDER_NAMES:
            return False
        return True

    def _remove_empty_dirs(self, root_path: Path) -> None:
        """루트 아래 빈 폴더 삭제. 출력 폴더(정리) 및 그 직하위 초성 폴더는 유지, 나머지 빈 폴더 제거."""
        dirs_to_check = [
            p for p in root_path.rglob("*")
            if self._is_dir_candidate_for_removal(root_path, p)
        ]
        dirs_to_check.sort(key=lambda p: len(p.relative_to(root_path).parts), reverse=True)
        for dir_path in dirs_to_check:
            if dir_path.exists() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                except OSError:
                    pass

    def _init_result_counts(self, result: OrganizeByChosungResult) -> None:
        """결과 객체에 초성 폴더별 카운트 초기화."""
        for name in FOLDER_NAMES:
            result.counts_by_folder[name] = 0

    def _log_completion(self, result: OrganizeByChosungResult) -> None:
        """정리 완료 디버그 로그 출력."""
        debug_step(
            self._log_sink,
            "organize_by_chosung_completed",
            {
                "total_processed": result.total_processed,
                "moved_or_copied": result.moved_or_copied,
                "skipped": result.skipped,
                "counts_by_folder": result.counts_by_folder,
            },
        )

    def execute(
        self,
        root_path: Path,
        move: bool = True,
        dry_run: bool = False,
    ) -> OrganizeByChosungResult:
        """초성별로 폴더를 만들고 하위 포함 모든 파일을 이동/복사합니다.

        Args:
            root_path: 대상 루트 폴더.
            move: True면 이동, False면 복사.
            dry_run: True면 폴더 생성 및 이동/복사 없이 계획만 반환.

        Returns:
            처리 결과 요약.
        """
        debug_step(
            self._log_sink,
            "organize_by_chosung_start",
            {"root_path": str(root_path), "move": move, "dry_run": dry_run},
        )
        result = OrganizeByChosungResult()
        self._init_result_counts(result)

        if not root_path.is_dir():
            return result

        files = self._collect_all_files_recursive(root_path)
        target_base = root_path / OUTPUT_SUBFOLDER
        if not files:
            result.files_already_in_chosung = self._count_files_in_output(target_base)
        if dry_run:
            return self._apply_dry_run(files, result)

        self._apply_move_or_copy(target_base, files, move, result)
        if move:
            self._remove_empty_dirs(root_path)
        self._log_completion(result)
        return result
