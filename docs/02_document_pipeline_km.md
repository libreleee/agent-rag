# 02. KM 문서 파싱 및 전처리 파이프라인

사내 지식 관리(KM) 시스템의 성패는 **다양한 포맷의 비정형 문서를 얼마나 손실 없이 기계 및 LLM이 이해하기 쉬운 구조(Markdown/JSON)로 변환하는가**에 달려 있습니다.

---

## 1. 포맷별 파싱 전략 및 권장 라이브러리

| 파일 형식 | 주요 특징 및 난제 | 추천 도구 / 라이브러리 | 전처리 핵심 전략 |
| :--- | :--- | :--- | :--- |
| **HWP / HWPX** | 국내 공공/기업 표준, 바이너리 포맷(HWP 5.0), 복잡한 중첩 표 | `pywin32` (Windows OLE), `pyhwp`, `xml.etree` (HWPX 파싱) | • HWPX의 경우 압축 해제 후 XML 직접 파싱<br>• 복잡한 표를 Markdown Table(`\| col1 \| col2 \|`)로 변환 |
| **PPT / PPTX** | 세미나/발표 자료, 슬라이드별 압축 문장, 발표자 노트(Notes) 존재 | `python-pptx`, `unstructured` | • **발표자 노트(Speaker Notes) 반드시 추출**<br>• 슬라이드 번호/제목 단위로 1개 청크 묶기 |
| **PDF** | 복잡한 다단 레이아웃, 차트/다이어그램, 스캔본(OCR 필요) | `docling`, `pypdf`, `pymupdf`, `mineru` | • Docling을 활용한 레이아웃 분석 및 표 구조화<br>• 수식 및 표를 Markdown으로 고품질 변환 |
| **Word / Excel** | 표준 비즈니스 문서, 다중 시트, 통계 데이터 | `python-docx`, `pandas`, `openpyxl` | • Excel 시트별 요약 및 CSV/Markdown 변환<br>• Word 헤더 레벨(H1, H2, H3) 기준 계층 분할 |

---

## 2. 세미나 자료(PPTX/PDF) 특화 전처리 전략

### ① 슬라이드 단위 청킹 (Slide-Level Chunking)
* PPTX/PDF 세미나 자료는 일반 문서처럼 문장 단위로 자르면 전후 맥락이 끊깁니다.
* **1개 슬라이드 = 1개 Document/Chunk** 구조를 기본으로 채택합니다.

### ② 발표자 노트(Speaker Notes) 통합
* 슬라이드 본문은 개조식(불릿) 키워드 위주이지만, 하단 발표자 메모에는 상세한 설명과 논리가 포함되어 있어 RAG 검색 품질을 극대화합니다.
* 파싱 결과 구조:
  ```markdown
  ## Slide 5: Agentic RAG 아키텍처 개요
  - 주요 구성: KM, RAG, Agent 엔진
  - 동작 방식: 다단계 라우팅 및 툴 실행

  [발표자 설명/노트]
  이 장표에서는 기존 단순 RAG의 한계를 극복하기 위해 LangGraph 기반의 상태 관리 에이전트를 도입한 배경과 세부 흐름을 설명합니다.
  ```

### ③ 시각 자료(다이어그램/차트) VLM 캡셔닝
* 텍스트가 적고 아키텍처 다이어그램/그래프가 중심인 슬라이드는 비전 모델(GPT-4o, Claude 3.5 Sonnet, Gemini Flash)을 통해 텍스트 요약 캡션을 생성하여 메타데이터로 함께 인덱싱합니다.

---

## 3. HWP / HWPX 파싱 및 표(Table) 구조 보존

### ① HWPX (개방형 한글 XML 포맷)
* HWPX 파일은 ZIP 압축 구조 내 `Contents/section0.xml` 등에 본문 및 표 데이터가 XML 형태로 저장됩니다.
* 파서가 XML의 `<hp:tbl>`(표), `<hp:tr>`(행), `<hp:tc>`(열) 태그를 파싱하여 Markdown Table로 변환합니다.

### ② HWP (바이너리 포맷)
* Windows 환경: `win32com.client` (한컴오피스 한글 자동화)를 사용해 HWPX 또는 텍스트/HTML로 일괄 변환 후 처리.
* 리눅스/컨테이너 환경: `pyhwp` 라이브러리로 텍스트 스트림 추출.

---

## 4. 메타데이터 스키마 설계

각 문서 청크에는 검색 필터링 및 권한 관리를 위한 메타데이터를 반드시 부착합니다.

```json
{
  "chunk_id": "doc_pptx_202508_slide_05",
  "source_file": "2025_AI_Agent_Architecture.pptx",
  "file_type": "pptx",
  "document_category": "기술세미나",
  "created_at": "2025-08-10",
  "department": "AI연구팀",
  "access_level": "public",
  "slide_number": 5,
  "has_table": false,
  "content": "## Slide 5: Agentic RAG 아키텍처 개요\n..."
}
```
