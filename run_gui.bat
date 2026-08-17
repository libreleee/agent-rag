@echo off
chcp 65001 > nul
title HWP to PDF Converter GUI
echo ========================================================
echo  한글(HWP / HWPX) to PDF 폴더 일괄 변환 GUI 실행 중...
echo ========================================================
uv run python gui_converter.py
pause
