"""OrganizeByChosungUseCase 및 초성 폴더명 유틸 테스트."""
from pathlib import Path

from application.use_cases.organize_by_chosung import (
    FOLDER_NAMES,
    OUTPUT_SUBFOLDER,
    effective_stem_for_sort,
    get_chosung_folder_name,
    normalize_target_filename,
    OrganizeByChosungUseCase,
)


class TestGetChosungFolderName:
    """get_chosung_folder_name 유틸 테스트."""

    def test_empty_string_returns_others(self):
        assert get_chosung_folder_name("") == "기타"

    def test_hangul_ga_returns_g_group(self):
        assert get_chosung_folder_name("가") == "ㄱ-ㄷ"

    def test_hangul_na_returns_g_group(self):
        assert get_chosung_folder_name("나") == "ㄱ-ㄷ"

    def test_hangul_da_returns_g_group(self):
        assert get_chosung_folder_name("다") == "ㄱ-ㄷ"

    def test_hangul_ra_returns_r_group(self):
        assert get_chosung_folder_name("라") == "ㄹ-ㅂ"

    def test_double_consonant_gga_maps_to_g_group(self):
        assert get_chosung_folder_name("까") == "ㄱ-ㄷ"

    def test_double_consonant_dda_maps_to_d_group(self):
        assert get_chosung_folder_name("따") == "ㄱ-ㄷ"

    def test_double_consonant_bba_maps_to_b_group(self):
        assert get_chosung_folder_name("빠") == "ㄹ-ㅂ"

    def test_digit_returns_09_folder(self):
        assert get_chosung_folder_name("0") == "0-9"
        assert get_chosung_folder_name("9") == "0-9"

    def test_english_returns_az_folder(self):
        assert get_chosung_folder_name("A") == "A-Z"
        assert get_chosung_folder_name("z") == "A-Z"

    def test_folder_names_constant_has_groups_az_09_others(self):
        assert len(FOLDER_NAMES) == 7
        assert FOLDER_NAMES[:4] == ("ㄱ-ㄷ", "ㄹ-ㅂ", "ㅅ-ㅈ", "ㅊ-ㅎ")
        assert FOLDER_NAMES[4:7] == ("A-Z", "0-9", "기타")


class TestEffectiveStemForSort:
    """effective_stem_for_sort 유틸 테스트."""

    def test_strips_brackets(self):
        assert effective_stem_for_sort("[Novel] 가나다") == "가나다"
        assert effective_stem_for_sort("(2024) Title") == "Title"

    def test_strips_multiple_brackets(self):
        assert effective_stem_for_sort("[Tag] (2024) 가나다") == "가나다"

    def test_plain_stem_unchanged(self):
        assert effective_stem_for_sort("가나다") == "가나다"
        assert effective_stem_for_sort("Hello") == "Hello"

    def test_empty_after_strip_returns_empty(self):
        assert effective_stem_for_sort("[Only]") == ""


class TestNormalizeTargetFilename:
    """normalize_target_filename 유틸 테스트."""

    def test_strips_trailing_numbered_suffix(self):
        assert normalize_target_filename("가나다 (1).txt") == "가나다.txt"
        assert normalize_target_filename("file (2).txt") == "file.txt"

    def test_strips_numbered_suffix_with_trailing_dot(self):
        """확장자 앞에 점이 하나 더 있는 경우(..txt)도 ' (1)' 제거."""
        assert normalize_target_filename("가수 5회차 천재 매니저 1-148 본편 완결 (1)..txt") == "가수 5회차 천재 매니저 1-148 본편 완결.txt"

    def test_plain_name_unchanged(self):
        assert normalize_target_filename("가나다.txt") == "가나다.txt"
        assert normalize_target_filename("file.txt") == "file.txt"


class TestOrganizeByChosungUseCase:
    """OrganizeByChosungUseCase 실행 테스트."""

    def test_execute_nonexistent_path_returns_empty_result(self, tmp_path: Path):
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path / "nonexistent", move=True, dry_run=True)
        assert result.total_processed == 0
        assert result.moved_or_copied == 0

    def test_execute_dry_run_counts_only(self, tmp_path: Path):
        (tmp_path / "가나다.txt").write_text("a")
        (tmp_path / "마바사.txt").write_text("b")
        (tmp_path / "123.txt").write_text("c")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=True)
        assert result.total_processed == 3
        assert result.moved_or_copied == 3
        assert result.counts_by_folder.get("ㄱ-ㄷ", 0) >= 1  # 가나다 -> ㄱ-ㄷ
        assert result.counts_by_folder.get("ㄹ-ㅂ", 0) >= 1  # 마바사 -> ㄹ-ㅂ
        assert result.counts_by_folder.get("0-9", 0) >= 1  # 123 -> 0-9
        # dry_run이므로 디렉터리 생성/이동 없음
        assert not (tmp_path / OUTPUT_SUBFOLDER).exists()
        assert (tmp_path / "가나다.txt").exists()

    def test_execute_move_creates_folders_and_moves_files(self, tmp_path: Path):
        (tmp_path / "가나다.txt").write_text("a")
        (tmp_path / "나다라.txt").write_text("b")
        (tmp_path / "other.txt").write_text("c")  # ASCII so 기타 folder
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.total_processed == 3
        assert result.moved_or_copied == 3
        out = tmp_path / OUTPUT_SUBFOLDER
        assert (out / "ㄱ-ㄷ").is_dir()
        assert (out / "A-Z").is_dir()
        assert (out / "ㄱ-ㄷ" / "가나다.txt").exists()
        assert (out / "ㄱ-ㄷ" / "나다라.txt").exists()
        assert (out / "A-Z" / "other.txt").exists()
        assert not (tmp_path / "가나다.txt").exists()
        assert not (tmp_path / "나다라.txt").exists()
        assert not (tmp_path / "other.txt").exists()

    def test_execute_copy_leaves_originals(self, tmp_path: Path):
        (tmp_path / "가.txt").write_text("a")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=False, dry_run=False)
        assert result.moved_or_copied == 1
        assert (tmp_path / "가.txt").exists()
        assert (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "가.txt").exists()

    def test_execute_move_flat_under_chosung(self, tmp_path: Path):
        """하위 폴더 파일도 초성 폴더 바로 아래로만 이동 (하위 폴더 없음)."""
        (tmp_path / "sub" / "deep").mkdir(parents=True)
        (tmp_path / "sub" / "deep" / "가나다.txt").write_text("a")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.total_processed == 1
        assert result.moved_or_copied == 1
        assert (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "가나다.txt").exists()
        assert not (tmp_path / "sub" / "deep" / "가나다.txt").exists()

    def test_execute_same_name_in_different_dirs_gets_unique_name(self, tmp_path: Path):
        """서로 다른 하위 폴더의 같은 파일명은 초성 폴더에서 번호로 구분."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "가.txt").write_text("1")
        (tmp_path / "b" / "가.txt").write_text("2")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.total_processed == 2
        assert result.moved_or_copied == 2
        chosung_dir = tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ"
        files_in_chosung = list(chosung_dir.iterdir())
        assert len(files_in_chosung) == 2
        names = {p.name for p in files_in_chosung}
        assert "가.txt" in names
        assert any("(1)" in n for n in names)

    def test_execute_dry_run_counts_recursive(self, tmp_path: Path):
        """재귀 수집: 직하위 + 하위 폴더 파일 모두 집계."""
        (tmp_path / "가.txt").write_text("a")
        (tmp_path / "b").mkdir()
        (tmp_path / "b" / "나.txt").write_text("b")
        (tmp_path / "c" / "d").mkdir(parents=True)
        (tmp_path / "c" / "d" / "다.txt").write_text("c")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=True)
        assert result.total_processed == 3
        assert result.counts_by_folder.get("ㄱ-ㄷ", 0) == 3  # 가, 나, 다

    def test_execute_move_removes_empty_dirs(self, tmp_path: Path):
        """이동 후 빈 폴더는 삭제됨. 복사 시에는 삭제하지 않음."""
        (tmp_path / "sub" / "deep").mkdir(parents=True)
        (tmp_path / "sub" / "deep" / "가.txt").write_text("a")
        use_case = OrganizeByChosungUseCase()
        use_case.execute(tmp_path, move=True, dry_run=False)
        assert not (tmp_path / "sub").exists()
        assert (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "가.txt").exists()

    def test_execute_uses_effective_stem_bracket_stripped(self, tmp_path: Path):
        """앞에 [] () 가 있으면 제거한 뒤의 제목으로 분류."""
        (tmp_path / "[Novel] 가나다.txt").write_text("a")
        (tmp_path / "(2024) Apple.txt").write_text("b")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.total_processed == 2
        assert result.moved_or_copied == 2
        out = tmp_path / OUTPUT_SUBFOLDER
        assert (out / "ㄱ-ㄷ" / "[Novel] 가나다.txt").exists()
        assert (out / "A-Z" / "(2024) Apple.txt").exists()

    def test_execute_strips_1_from_target_name(self, tmp_path: Path):
        """원본 이름 끝 ' (1)' 은 대상 파일명에서 제거됨."""
        (tmp_path / "가나다 (1).txt").write_text("a")
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.moved_or_copied == 1
        assert (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "가나다.txt").exists()
        assert not (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "가나다 (1).txt").exists()

    def test_execute_collects_files_inside_chosung_subdirs(self, tmp_path: Path):
        """초성 구간 폴더(ㄱ-ㄷ 등) 안의 하위 폴더에 있는 파일도 수집·이동하고 빈 하위 폴더 제거."""
        (tmp_path / "ㄱ").mkdir()
        (tmp_path / "ㄱ" / "sub").mkdir()
        (tmp_path / "ㄱ" / "sub" / "나.txt").write_text("b")  # 나 -> ㄱ-ㄷ
        use_case = OrganizeByChosungUseCase()
        result = use_case.execute(tmp_path, move=True, dry_run=False)
        assert result.total_processed == 1
        assert result.moved_or_copied == 1
        assert (tmp_path / OUTPUT_SUBFOLDER / "ㄱ-ㄷ" / "나.txt").exists()
        assert not (tmp_path / "ㄱ" / "sub").exists()
