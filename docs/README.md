# 🧠 AI Agentic Knowledge Hub

본 문서는 사내/외 다양한 형태의 문서(HWP, PDF, PPTX, DOCX, XLSX 등)를 지식 자산(Knowledge Mesh)으로 구축하고, 이를 인간 사용자(GUI/Web)와 AI 에이전트(MCP/REST)가 모두 공통으로 활용할 수 있도록 지원하는 **AI Agentic Knowledge Hub**의 종합 기술 설계 및 배포 가이드입니다.

---

## 📚 전체 문서 목차

### 1. 🏛️ 시스템 아키텍처, 환경 구축 및 배포 가이드
* **[📁 00. 아키텍처 및 턴키 배포 마스터 개요](./hub_architecture_and_deployment/README.md)**
* **[🏗️ 01. 프로젝트 디렉토리 아키텍처 및 `uv` 환경 구축 가이드](./hub_architecture_and_deployment/01_project_structure_and_setup.md)**
  - 소스코드 디렉토리 트리 및 파일별 역할 상세
  - `uv` 기반 3초 초고속 가상환경 생성 및 의존성 설치 (`uv sync`)
  - 윈도우/리눅스 외부 렌더러 설정 및 E2E 테스트 검증
* **[🌐 02. 다중 인터페이스 실행 및 외부 연동 가이드](./hub_architecture_and_deployment/02_multi_interface_integration_guide.md)**
  - 3대 실행 모드 (FastAPI 웹 서버, 윈도우 GUI, AI 에이전트 MCP 서버)
  - 웹/앱(JavaScript/Fetch), 타 백엔드(REST API), AI 에이전트(MCP), Python SDK 연동 예제

---

### 2. 📝 고품질 Word (.docx) 변환 기술 문서 (신규)
* **[📁 00. 고품질 Word 변환 기술 개요](./high_fidelity_word_conversion/README.md)**
* **[📝 01. 한글 (HWP/HWPX) ➔ 고품질 Word 레이아웃 역공학 복원 기술 분석](./high_fidelity_word_conversion/01_hwp_to_docx_layout_reconstruction.md)**
  - 기존 텍스트 추출 방식의 표/서식 깨짐 원인 분석
  - `rhwp` (Rust 벡터 렌더러) + `pdf2docx` (레이아웃 역공학 엔진) 2단계 하이브리드 파이프라인
  - 1세대 방식 vs LibreOffice vs 2단계 하이브리드 엔진 비교 벤치마크

---

### 3. 📑 포맷별 문서 수집 및 임베딩 표준 가이드
* **[📁 00. 문서 수집 및 임베딩 아키텍처 개요](./document_ingestion/README.md)**
* **[📄 01. 한글 문서 (HWP / HWPX) 듀얼 엔진 파싱 및 변환 가이드](./document_ingestion/01_hwp_hwpx_guide.md)**
* **[📑 02. PDF 문서 파싱 및 표 추출 가이드](./document_ingestion/02_pdf_guide.md)**
* **[📊 03. 프레젠테이션 (PPTX / PPT) 슬라이드 & 노트 가이드](./document_ingestion/03_pptx_guide.md)**
* **[📝 04. MS 워드 (DOCX / DOC) 계층 파싱 가이드](./document_ingestion/04_docx_guide.md)**
* **[📈 05. 스프레드시트 (XLSX / CSV) 표 데이터 구조화 가이드](./document_ingestion/05_xlsx_csv_guide.md)**
* **[🌐 06. 텍스트 / 마크다운 / 웹페이지 (HTML) 파싱 가이드](./document_ingestion/06_txt_markdown_html_guide.md)**

---

### 4. 🧠 에이전틱 RAG & 모델 학습 파이프라인
* **[01. 시스템 아키텍처 및 핵심 개념](./01_system_architecture.md)**
* **[02. KM 문서 파싱 및 전처리 파이프라인](./02_document_pipeline_km.md)**
* **[03. 추론(RAG) 및 모델 학습(Training) 파이프라인](./03_agentic_rag_and_training.md)**
* **[04. No-Code / Low-Code 플랫폼 설계](./04_nocode_lowcode_platform.md)**
