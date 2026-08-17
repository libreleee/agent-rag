@echo off
chcp 65001 > nul
title AI Agentic Knowledge Hub - MCP Server
echo ========================================================
echo  AI Agentic Knowledge Hub - MCP Server (Stdio) 실행 중...
echo ========================================================
uv run python src/mcp_server.py
pause
