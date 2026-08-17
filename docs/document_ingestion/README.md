# 📚 문서 포맷별 수집·임베딩 및 Hub 등록 표준 가이드
*(Document Ingestion & Embedding Architecture Guide)*

본 문서는 **AI Agentic Knowledge Hub**에 사내외 다양한 비정형/정형 문서를 등록하고, 구조적 손실 없이 파싱하여 고성능 벡터/하이브리드 지식 베이스로 임베딩하기 위한 **포맷별 표준 기술 사양 및 파이프라인 정의서**입니다.

---

## 🎯 핵심 설계 철학: "Lossless Structuring (구조 무손실 정형화)"

단순한 텍스트 추출(`Plain Text Extraction`)은 표(Table), 제목 계층(Heading Hierarchy), 슬라이드 발표자 노트(Speaker Notes) 등의 중요한 문맥을 파괴합니다.  
본 시스템은 모든 문서 포맷을 **구조화된 마크다운(Structured Markdown) 및 메타데이터**로 1차 정규화한 뒤 임베딩합니다.

```
 [ 원본 다양한 문서 포맷 ]
 (HWP, HWPX, PDF, PPTX, DOCX, XLSX, CSV, HTML, TXT)
                        │
                        ▼ (포맷별 특화 파서 & 변환 엔진)
 ┌─────────────────────────────────────────────────────────────┐
 │           1단계: 무손실 구조화 (Lossless Extraction)         │
 │  • 제목 계층(H1~H4) 태깅   • 표(Table) 마크다운 완벽 복원    │
 │  • 슬라이드 노트 분리 추출   • 이미지 캡션 및 메타데이터 추출│
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │           2단계: 시맨틱 청킹 (Semantic Chunking)            │
 │  • 단락/섹션 경계 분할     • 표 단위 청크 보존 (행 분할 방지)│
 │  • 오버랩 150자 유지       • 계층적 부모-자식 메타 태깅      │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │           3단계: 하이브리드 인덱싱 & Hub 등록 (Dual Mesh)    │
 │  • Dense Embedding: BAAI/bge-m3 ➔ ChromaDB 저장             │
 │  • Sparse Index: BM25 형태소 분석 ➔ 역색인 저장             │
 │  • Multi-Protocol 노출: GUI / Web / REST API / MCP Server   │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📊 지원 포맷별 파이프라인 매트릭스

| 포맷 | 주요 용도 | 사용 도구/엔진 | 핵심 추출 포인트 | 상세 가이드 링크 |
| :--- | :--- | :--- | :--- | :--- |
| **HWP / HWPX** | 공공/사내 기안문, 규정집 | Pure Python XML Parser / LibreOffice Headless | 표(Table) 완벽 복원, HWP ➔ PDF 변환 | [01_hwp_hwpx_guide.md](./01_hwp_hwpx_guide.md) |
| **PDF** | 논문, 매뉴얼, 공시자료 | PyMuPDF (Fitz) / PDFplumber / OCR (Surya/Paddle) | 2단 컬럼 재구성, 표 격자 복원, 텍스트 레이어 | [02_pdf_guide.md](./02_pdf_guide.md) |
| **PPTX / PPT** | 세미나 발표자료, 기획서 | `python-pptx` / LibreOffice Headless | 슬라이드별 본문 + **발표자 노트(Notes)** 결합 | [03_pptx_guide.md](./03_pptx_guide.md) |
| **DOCX / DOC** | 기술 보고서, 표준 계약서 | `python-docx` / LibreOffice Headless | H1~H3 아웃라인 계층 구조, 각주/미주 보존 | [04_docx_guide.md](./04_docx_guide.md) |
| **XLSX / CSV** | 재무제표, 통계, 목록표 | `openpyxl` / `pandas` | 시트별 요약, 행 단위 의미론적 마크다운화 | [05_xlsx_csv_guide.md](./05_xlsx_csv_guide.md) |
| **TXT / MD / HTML** | 웹페이지, 소스코드 문서, 위키 | `trafilatura` / `BeautifulSoup4` / `markdown` | 불필요한 태그/광고 제거, 시맨틱 본문 정제 | [06_txt_markdown_html_guide.md](./06_txt_markdown_html_guide.md) |

---

## 🚀 AI Agentic Knowledge Hub 공통 등록 및 사용 인터페이스

모든 포맷의 문서는 변환/파싱 후 아래 4가지 경로 중 원하는 방식으로 즉시 등록 및 조회할 수 있습니다:

1. **데스크톱 폴더 일괄 등록 GUI (`run_gui.bat`)**
   - 폴더를 선택하면 내부의 모든 포맷 문서를 자동 감지하여 PDF 변환 및 ChromaDB에 일괄 인덱싱
2. **웹 포털 UI (`http://localhost:8001/`)**
   - 웹 화면에서 드래그 앤 드롭으로 업로드 ➔ 마크다운 추출 결과 및 인덱싱 청크 즉시 확인
3. **REST API 엔드포인트**
   - `POST /api/upload`: 파일 업로드 및 자동 파싱/인덱싱
   - `POST /api/convert_folder`: 폴더 단위 일괄 변환 및 인덱싱
   - `POST /api/search`: 하이브리드(Dense+Sparse) 지식 검색
4. **AI 에이전트 MCP Server (`src/mcp_server.py`)**
   - Claude Desktop, Cursor, Antigravity 등의 에이전트가 `index_document`, `convert_hwp_to_pdf`, `search_knowledge` 도구를 직접 호출
