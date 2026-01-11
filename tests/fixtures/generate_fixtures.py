"""테스트 픽스처 데이터 생성 스크립트.

다양한 시나리오를 테스트하기 위한 고정된 테스트 데이터셋을 생성합니다.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional


def create_directory_structure(base_path: Path) -> None:
    """디렉토리 구조 생성."""
    (base_path / "small").mkdir(parents=True, exist_ok=True)
    (base_path / "medium").mkdir(parents=True, exist_ok=True)
    (base_path / "edge_cases").mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    """파일 작성."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def create_exact_duplicates(base_path: Path) -> None:
    """완전 동일 파일 중복 생성 (소규모 데이터셋)."""
    small_dir = base_path / "small"
    
    # 동일한 내용의 파일 3개 (완전 중복)
    content = "소설 제목\n작가명\n\n1화\n내용입니다.\n"
    for i in range(1, 4):
        write_file(small_dir / f"novel_exact_dup_{i}.txt", content)
    
    # 다른 내용의 파일 2개
    write_file(small_dir / "novel_unique_1.txt", "다른 소설\n내용 A\n")
    write_file(small_dir / "novel_unique_2.txt", "또 다른 소설\n내용 B\n")


def create_normalized_duplicates(base_path: Path) -> None:
    """정규화 후 동일한 파일 생성 (소규모 데이터셋)."""
    small_dir = base_path / "small"
    
    # 공백/줄바꿈만 다른 동일 내용
    content_v1 = "소설 제목\r\n작가명\r\n\r\n1화\r\n내용입니다.\r\n"
    content_v2 = "소설 제목\n작가명\n\n1화\n내용입니다.\n"
    content_v3 = "소설 제목  \n작가명  \n  \n1화  \n내용입니다.  \n"
    
    write_file(small_dir / "novel_normalized_1.txt", content_v1)
    write_file(small_dir / "novel_normalized_2.txt", content_v2)
    write_file(small_dir / "novel_normalized_3.txt", content_v3)


def create_medium_dataset(base_path: Path) -> None:
    """중규모 데이터셋 생성 (100~500개 파일)."""
    medium_dir = base_path / "medium"
    
    # 여러 중복 그룹 생성
    for group_id in range(1, 11):  # 10개의 중복 그룹
        content = f"소설 그룹 {group_id}\n작가 {group_id}\n\n내용 그룹 {group_id}\n"
        for file_num in range(1, 6):  # 각 그룹당 5개 파일
            write_file(
                medium_dir / f"group_{group_id}_file_{file_num}.txt",
                content
            )
    
    # 고유 파일들
    for i in range(1, 51):  # 50개의 고유 파일
        write_file(
            medium_dir / f"unique_{i}.txt",
            f"고유 소설 {i}\n내용 {i}\n"
        )


def create_edge_cases(base_path: Path) -> None:
    """엣지 케이스 데이터셋 생성."""
    edge_dir = base_path / "edge_cases"
    
    # 1. 제목이 다르지만 내용 동일
    content = "1화\n본문 내용입니다.\n"
    write_file(edge_dir / "novel_title_A.txt", f"소설 A\n{content}")
    write_file(edge_dir / "novel_title_B.txt", f"소설 B\n{content}")
    
    # 2. 포함 관계 (1-114화 vs 1-158화)
    part1_114 = "\n".join([f"{i}화 내용" for i in range(1, 115)])
    part1_158 = "\n".join([f"{i}화 내용" for i in range(1, 159)])
    write_file(edge_dir / "novel_1-114.txt", f"소설 제목\n{part1_114}")
    write_file(edge_dir / "novel_1-158.txt", f"소설 제목\n{part1_158}")
    
    # 3. 인코딩이 섞인 텍스트
    utf8_content = "UTF-8 파일\n한글 내용입니다.\n"
    write_file(edge_dir / "novel_utf8.txt", utf8_content, encoding="utf-8")
    
    # EUC-KR 인코딩 파일
    try:
        euc_kr_content = "EUC-KR 파일\n한글 내용입니다.\n"
        write_file(edge_dir / "novel_euckr.txt", euc_kr_content, encoding="euc-kr")
    except (UnicodeEncodeError, LookupError):
        # Windows에서 euc-kr이 지원되지 않을 수 있음
        pass
    
    # 4. 빈 파일 (0 bytes)
    empty_file = edge_dir / "empty_file.txt"
    empty_file.parent.mkdir(parents=True, exist_ok=True)
    empty_file.touch()
    
    # 5. 매우 작은 파일 (< 512 bytes)
    write_file(edge_dir / "tiny_file.txt", "A")
    
    # 6. 매우 큰 파일 (대용량 테스트용, 실제로는 작은 크기로 생성)
    # 실제 대용량 파일은 생성하지 않고, 참고용으로만
    large_content = "대용량 파일 테스트\n" * 1000  # 실제로는 작게
    write_file(edge_dir / "large_file.txt", large_content)
    
    # 7. 바이너리 파일 (텍스트가 아닌 파일)
    binary_file = edge_dir / "binary.bin"
    binary_file.parent.mkdir(parents=True, exist_ok=True)
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
    
    # 8. 특수 문자 포함 파일
    special_content = "특수 문자 파일\n\n\t탭 문자\n줄바꿈\n\r\nCRLF\r\nLF\n"
    write_file(edge_dir / "special_chars.txt", special_content)


def main() -> None:
    """메인 함수."""
    script_dir = Path(__file__).parent
    base_path = script_dir
    
    print(f"테스트 픽스처 데이터 생성 중: {base_path}")
    
    # 디렉토리 구조 생성
    create_directory_structure(base_path)
    
    # 소규모 데이터셋
    print("소규모 데이터셋 생성 중...")
    create_exact_duplicates(base_path)
    create_normalized_duplicates(base_path)
    
    # 중규모 데이터셋
    print("중규모 데이터셋 생성 중...")
    create_medium_dataset(base_path)
    
    # 엣지 케이스
    print("엣지 케이스 데이터셋 생성 중...")
    create_edge_cases(base_path)
    
    print("완료!")
    print(f"생성된 파일 수:")
    print(f"  - small/: {len(list((base_path / 'small').glob('*')))} 파일")
    print(f"  - medium/: {len(list((base_path / 'medium').glob('*')))} 파일")
    print(f"  - edge_cases/: {len(list((base_path / 'edge_cases').glob('*')))} 파일")


if __name__ == "__main__":
    main()
