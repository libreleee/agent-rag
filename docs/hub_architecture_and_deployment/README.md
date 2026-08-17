# 🏛️ AI Agentic Knowledge Hub 아키텍처 및 턴키 배포 가이드
*(Architecture, Deployment & Multi-Platform Integration Manual)*

본 디렉터리는 **AI Agentic Knowledge Hub**를 다른 PC, 사내 서버, 클라우드 인프라에 **그대로 복제하여 5분 만에 동일하게 가동하고, 웹/앱/AI 에이전트와 연동하기 위한 마스터 가이드**입니다.

---

## 📚 가이드 목차

1. **[01. 프로젝트 디렉토리 아키텍처 및 `uv` 환경 구축 가이드](./01_project_structure_and_setup.md)**
   - 전체 파일 트리 및 모듈별 책임 정의
   - `uv` 기반 가상환경 생성 및 초고속 의존성 동기화 (`uv sync`)
   - 윈도우/리눅스 외부 렌더러(LibreOffice) 세팅 및 E2E 테스트 검증

2. **[02. 다중 인터페이스 실행 및 외부 연동 가이드](./02_multi_interface_integration_guide.md)**
   - 3대 실행 모드 (FastAPI 웹 서버, 윈도우 GUI, AI 에이전트 MCP 서버)
   - 웹/모바일 프론트엔드 (JavaScript Fetch) 호출 예제
   - 사내 시스템 / 타 백엔드 (Python / Java / C#) REST API 연동
   - Claude Desktop / Cursor / Antigravity MCP Server 설정법
   - Python SDK 직접 임포트 (`from src...`) 파이프라인

---

## ⚡ 퀵스타트 치트시트 (다른 환경에서 5분 만에 실행하기)

```bash
# 1. uv 가상환경 생성 및 패키지 동기화
uv venv --python 3.12
uv sync

# 2. 파이프라인 무결성 검증
uv run python test_pipeline.py

# 3. 원하는 인터페이스로 즉시 실행
# (A) 웹 대시보드 & REST API 서버 실행 ➔ http://localhost:8001
uv run uvicorn src.api.server:app --port 8001 --reload

# (B) 윈도우 탐색기 전용 GUI 실행
run_gui.bat

# (C) AI 에이전트 전용 MCP Server 실행
run_mcp_server.bat
```
