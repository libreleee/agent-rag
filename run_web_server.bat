@echo off
chcp 65001 > nul
echo ========================================================
echo   AI Agentic Knowledge Hub - Web & API Server
echo ========================================================
echo.
echo [1/2] 서버 시작 중... (Port: 8001)
echo.
echo 웹 대시보드 URL : http://localhost:8001/
echo API 문서 (Swagger) : http://localhost:8001/docs
echo.
echo 서버를 종료하려면 Ctrl+C 를 누르세요.
echo ========================================================
echo.

cd /d "%~dp0"
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8001 --reload

pause
