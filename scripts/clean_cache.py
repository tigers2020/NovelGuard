#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NovelGuard 파이캐시 삭제 스크립트

프로젝트 내의 모든 __pycache__ 폴더와 .pyc 파일을 삭제합니다.
"""

import shutil
import pathlib
from pathlib import Path


def clean_pycache(root_path: Path) -> int:
    """프로젝트 내의 모든 __pycache__ 폴더와 .pyc 파일을 삭제.
    
    Args:
        root_path: 프로젝트 루트 경로
        
    Returns:
        삭제된 폴더/파일 개수
    """
    deleted_count = 0
    
    # __pycache__ 폴더 삭제
    for pycache_dir in root_path.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                print(f"삭제됨: {pycache_dir}")
                deleted_count += 1
            except Exception as e:
                print(f"오류 (삭제 실패): {pycache_dir} - {e}")
    
    # .pyc 파일 삭제 (__pycache__ 외부에 있을 수 있는 파일)
    for pyc_file in root_path.rglob("*.pyc"):
        if pyc_file.is_file():
            try:
                pyc_file.unlink()
                print(f"삭제됨: {pyc_file}")
                deleted_count += 1
            except Exception as e:
                print(f"오류 (삭제 실패): {pyc_file} - {e}")
    
    return deleted_count


def main():
    """메인 함수."""
    # 스크립트가 있는 디렉토리의 상위(프로젝트 루트)로 이동
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    
    print(f"프로젝트 루트: {project_root}")
    print("파이캐시 삭제 시작...\n")
    
    deleted_count = clean_pycache(project_root)
    
    print(f"\n완료! 총 {deleted_count}개의 폴더/파일이 삭제되었습니다.")


if __name__ == "__main__":
    main()
