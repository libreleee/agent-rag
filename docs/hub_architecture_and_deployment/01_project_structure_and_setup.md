# 🏗️ 01. 프로젝트 디렉토리 아키텍처 및 `uv` 환경 구축 가이드

본 문서는 **AI Agentic Knowledge Hub** 프로젝트를 새로운 머신(Windows / Linux / macOS)에서 **처음부터 100% 동일하게 재현 및 구축(Turnkey Deployment)**하기 위한 상세 가이드입니다.

---

## 📁 1. 전체 디렉토리 구조 및 파일별 역할

```
e:\work\ai\agent\agent-rag\
│
├── 📜 pyproject.toml              # 프로젝트 메타데이터 및 의존성 정의 (uv 기반)
├── 📜 uv.lock                     # 정확한 패키지 버전 고정 잠금 파일
├── 📜 .python-version             # 권장 Python 버전 (3.10 이상 권장, 3.12 지원)
├── 📜 mcp_config.json             # Claude Desktop / Cursor용 MCP 서버 설정 파일
│
├── 🚀 run_gui.bat                 # 윈도우 데스크톱 GUI 일괄 변환기 원클릭 실행 배치
├── 🚀 run_mcp_server.bat          # AI 에이전트용 표준 MCP Server 원클릭 실행 배치
├── 🐍 gui_converter.py            # 윈도우 Native Desktop GUI 프로그램 (Tkinter/ttk)
├── 🐍 test_pipeline.py            # 파싱-인덱싱-하이브리드 검색 E2E 검증 테스트 스크립트
│
├── 📂 src/                        # 핵심 백엔드 소스코드
│   ├── 🐍 __init__.py
│   │
│   ├── 📂 core/                   # 전역 설정 및 환경변수 관리
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 config.py           # 경로, 모델명, 청크 사이즈 전역 Pydantic Settings
│   │
│   ├── 📂 utils/                  # 범용 변환 유틸리티
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 hwp_to_pdf.py       # rhwp Rust 엔진 + LibreOffice 폴백 HWP/HWPX ➔ PDF 변환기
│   │   └── 🐍 hwp_to_docx.py      # python-docx + 구조화 파서 기반 HWP/HWPX ➔ Word(.docx) 서식 변환기
│   │
│   ├── 📂 parsers/                # 포맷별 무손실 구조화 파서
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 hwp_parser.py       # HWP 듀얼 엔진 하이브리드 파서 (rhwp + LibreOffice+PyMuPDF)
│   │   ├── 🐍 hwpx_parser.py      # HWPX 순수 XML 파서 (표 완벽 복원)
│   │   ├── 🐍 pptx_parser.py      # PPTX 슬라이드 본문 + 발표자 노트(Notes) 파서
│   │   ├── 🐍 pdf_parser.py       # PDF 페이지별 구조화 파서 (PyMuPDF)
│   │   └── 🐍 unified_parser.py   # 확장자별 최적 파서 자동 라우터
│   │
│   ├── 📂 rag/                    # 하이브리드 지식 베이스 엔진
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 indexer.py          # ChromaDB 벡터 스토어 청킹 및 메타데이터 인덱서
│   │   └── 🐍 retriever.py        # Dense Vector + Sparse BM25 (RRF 가중치 결합) 하이브리드 검색기
│   │
│   ├── 📂 api/                    # 웹 포털 & REST API 게이트웨이
│   │   ├── 🐍 server.py           # FastAPI 서버 (포트 8001, CORS, 업로드, 변환, 검색 라우트)
│   │   └── 📂 static/
│   │       └── 🌐 index.html      # No-Code 웹 대시보드 SPA (카탈로그/변환/등록/검색)
│   │
│   └── 🐍 mcp_server.py           # Model Context Protocol (MCP) 표준 서버 (6개 AI 도구 탑재)
│
├── 📂 data/                       # 로컬 영구 스토리지 (자동 생성)
│   ├── 📂 raw/                    # 업로드된 원본 문서 보관함
│   ├── 📂 processed/              # 추출된 구조화 Markdown 보관함
│   ├── 📂 vectordb/               # ChromaDB 임베딩 벡터 데이터베이스
│   └── 📂 temp/                   # 실시간 변환용 임시 버퍼
│
└── 📂 docs/                       # 기술 명세 및 가이드 문서
    ├── 📜 README.md               # 문서 전체 목차
    ├── 📂 document_ingestion/     # 포맷별(HWP, PDF, PPTX, DOCX, XLSX 등) 수집·임베딩 가이드
    └── 📂 hub_architecture_and_deployment/ # 본 시스템 구조 및 배포/연동 가이드
```

---

## ⚡ 2. `uv` 기반 가상환경 구축 (처음부터 설치하기)

본 프로젝트는 초고속 Python 패키지 관리자인 **`uv`**를 표준으로 사용합니다.

### 1단계: `uv` 설치 (시스템 미설치 시)
* **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
* **Linux / macOS**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2단계: 프로젝트 디렉토리 생성 및 초기화
```bash
# 1. 작업 디렉토리 이동
cd /path/to/your/workspace/agent-rag

# 2. Python 3.12 기반 uv 가상환경 생성
uv venv --python 3.12

# 3. 가상환경 활성화 (선택 사항, uv run 사용 시 자동 감지)
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
```

### 3단계: 필수 의존성 패키지 설치
이미 프로젝트에 `pyproject.toml`과 `uv.lock`이 있으므로 아래 명령어 **한 줄**로 모든 패키지가 3초 만에 완벽히 설치됩니다:
```bash
uv sync
```

*(참고: 패키지를 개별 설치할 때 사용한 핵심 라이브러리 목록)*
```bash
# 핵심 웹/API 및 MCP
uv add fastapi uvicorn pydantic pydantic-settings python-multipart mcp

# 고품질 문서 파서 및 변환기
uv add rhwp-python pymupdf python-pptx openpyxl pandas trafilatura

# RAG & 임베딩 & 검색
uv add langchain langchain-community chromadb rank-bm25 sentence-transformers
```

---

## 🏛️ 3. 외부 시스템 의존성 (LibreOffice)

HWP 및 오피스 문서의 2차 폴백 렌더링을 위해 **LibreOffice**가 권장됩니다:
* **Windows**: [LibreOffice 공식 다운로드](https://ko.libreoffice.org/download/download/) (기본 경로: `C:\Program Files\LibreOffice\program\soffice.exe`)
* **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y libreoffice
  ```
* **macOS**:
  ```bash
  brew install --cask libreoffice
  ```
*(참고: HWP/HWPX의 1차 핵심 파싱 및 PDF 변환은 내장된 `rhwp-python` Rust 엔진에 의해 LibreOffice 없이도 완벽하게 단독 실행됩니다.)*

---

## ✅ 4. 설치 검증 (E2E 테스트)

터미널에서 아래 명령을 실행하여 모든 파이프라인(파싱, 인덱싱, 하이브리드 검색)이 정상 동작하는지 3초 만에 검증합니다:
```bash
uv run python test_pipeline.py
```
출력 마지막에 `=== 모든 파이프라인 테스트가 성공적으로 완료되었습니다! ===`가 나오면 모든 준비가 끝난 것입니다.
