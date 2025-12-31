@echo off
REM NovelGuard 실행 스크립트 (CMD)
REM 한글 인코딩 문제 해결을 위한 설정 포함

REM 콘솔 코드 페이지를 UTF-8로 변경
chcp 65001 >nul

REM Python 스크립트 실행
python src/main.py

