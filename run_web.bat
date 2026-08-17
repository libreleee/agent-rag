@echo off
chcp 65001 > nul
title AI Agentic Knowledge Hub - Web Server

rem 포트 변경이 필요하면 아래 값을 수정하세요.
rem 8000번은 Supabase(kong) 게이트웨이가 선점하고 있어 기본값을 8077로 둡니다.
set HOST=127.0.0.1
set PORT=8077

echo ========================================================
echo  AI Agentic Knowledge Hub - Web Server 실행 중...
echo ========================================================
echo.
echo   웹 대시보드 : http://%HOST%:%PORT%
echo   Swagger API : http://%HOST%:%PORT%/docs
echo.
echo   (종료하려면 이 창에서 Ctrl+C 를 누르세요)
echo ========================================================

uv run uvicorn src.api.server:app --host %HOST% --port %PORT%
pause
