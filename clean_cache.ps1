# NovelGuard 파이캐시 삭제 스크립트 (PowerShell)
# 한글 인코딩 문제 해결을 위한 설정 포함

# 콘솔 인코딩을 UTF-8로 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Python 스크립트 실행
python scripts/clean_cache.py

# 일시 정지 (결과 확인용)
Read-Host "Press Enter to continue"
