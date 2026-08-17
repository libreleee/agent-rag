# 📄 01. 한글 문서 (HWP / HWPX) 듀얼 엔진 파싱, PDF 및 Word (.docx) 변환 가이드

본 문서는 한국 공공기관 및 기업의 핵심 자산인 한글 문서(`.hwp`, `.hwpx`)를 **AI Agentic Knowledge Hub**에서 **PDF 및 Word (.docx)**로 고품질 변환하고, 지식 베이스로 임베딩하기 위한 **기술 가이드 및 명세서**입니다.

---

## 🎯 1. 변환 및 파싱 파이프라인 개요

단일 툴에만 의존하지 않고, **Rust 기반의 초고속 엔진(`rhwp`)**, **네이티브 Word 빌더(`python-docx`)**, **오피스 렌더링 엔진(`LibreOffice`)**을 결합하여 **PDF 변환, Word (.docx) 변환, RAG 구조화 파싱**을 모두 완벽하게 지원합니다.

```
                        [ 한글 문서 입력 (.hwp / .hwpx) ]
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
   [ 1. PDF 무손실 변환 ]    [ 2. Word (.docx) 서식 변환 ]   [ 3. RAG 마크다운 파싱 ]
   • rhwp Rust PDF 렌더러    • python-docx 네이티브 생성     • rhwp 문단/섹션 추출
   • 폰트/레이아웃 100% 보존 • 표(Table) 격자 완벽 복원      • 표 마크다운 자동 변환
   • LibreOffice 폴백 지원   • H1~H3 제목 아웃라인 매핑      • ChromaDB + BM25 적재
```

---

## 🛠️ 2. 사용 엔진 및 역할 분담

| 엔진 / 라이브러리 | 주요 역할 | 특징 |
| :--- | :--- | :--- |
| **`rhwp-python` (Rust)** | **HWP ➔ PDF 초고속 렌더링 & 텍스트 추출** | • 한글 프로그램 없이 바이너리 HWP 직접 파싱 및 PDF 생성 |
| **`python-docx`** | **HWP ➔ Word (.docx) 네이티브 문서 빌더** | • 파싱된 마크다운 구조(제목, 문단, 표)를 표준 Word 스타일로 생성 |
| **`LibreOffice Headless`** | **2차 앙상블 & 오피스 포맷 폴백** | • `.doc`, `.ppt` 등 레거시 오피스 파일 변환 지원 |
| **`HwpxParser` (Pure XML)** | **HWPX 개방형 표준 전용 파서** | • XML 구조 직접 해석으로 표/스타일 무손실 추출 |

---

## 💻 3. Word (.docx) 변환 구현 원리 (`src/utils/hwp_to_docx.py`)

1. **구조화 파싱**: `UnifiedDocumentParser`가 HWP/HWPX의 본문, 제목(`Heading`), 마크다운 표(`| col | col |`)를 추출
2. **Word 네이티브 스타일 매핑**:
   - `# 제목` ➔ Word `Heading 1` (Pt 16)
   - `## 소제목` ➔ Word `Heading 2` (Pt 12)
   - `| 표 데이터 |` ➔ Word `Table` 객체 생성, 첫 행 배경 음영(Shading) 및 테두리(Border) 적용
   - `* 글머리 기호` ➔ Word `List Bullet` 스타일 적용
   - `**굵은 글씨**` ➔ Word Inline `Run.bold = True` 적용

---

## 🚀 4. 다중 인터페이스 사용 방법

### 1) 윈도우 데스크톱 GUI (`run_gui.bat`)
* 폴더 선택 ➔ **`[ ● Word 문서 (*.docx) ]`** 선택 ➔ **`[ 🚀 전체 일괄 변환 시작 ]`**
* 폴더 내 모든 한글 문서가 서식을 유지한 `.docx` 파일로 일괄 저장됩니다.

### 2) 웹 포털 대시보드 (`http://localhost:8001/`)
* **개별 변환**: 파일 드래그 앤 드롭 ➔ **`[ 📝 Word 변환 ]`** 선택 ➔ 즉시 다운로드
* **폴더 일괄 변환**: 폴더 경로 입력 ➔ **`[ 📝 Word 문서 ]`** 선택 ➔ 원클릭 일괄 변환

### 3) AI 에이전트 MCP Tool 호출 (Claude / Cursor)
```json
{
  "tool": "convert_document_to_word",
  "arguments": {
    "file_path": "C:/Users/Documents/사업계획서.hwp",
    "output_dir": "C:/Users/Documents/docx_output"
  }
}
```

### 4) REST API 호출 (cURL / Python)
```bash
# 단일 파일 Word 변환 다운로드
curl -X POST "http://localhost:8001/api/convert_hwp_to_docx" \
     -F "file=@/path/to/문서.hwp" \
     -o output.docx

# 폴더 일괄 Word 변환
curl -X POST "http://localhost:8001/api/convert_folder" \
     -H "Content-Type: application/json" \
     -d '{"input_folder": "E:/HWP_Files", "target_format": "docx"}'
```
