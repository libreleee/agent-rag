# 지식 적재 ➔ 학습 ➔ 추론 ➔ API 제공 통합 구현 명세

문서 하나로 **문서를 지식 베이스에 넣고, 그것으로 학습하고, 추론에 쓰고, API로 제공하는**
전 과정을 정의합니다. 본 문서만으로 구현에 착수할 수 있도록 현재 상태·목표 설계·작업 순서·
검증 기준을 모두 담습니다.

작성 기준일: 2026-08-17 / 대상 코드베이스: `agent-rag`

---

## 1. 이 문서를 쓰는 이유

현재 시스템은 문서를 **변환**하고 **검색**할 수 있지만, 그 지식을 **학습에 쓸 수 없는 형태**로
저장하고 있습니다. 파싱 결과가 곧바로 800자 청크로 잘려 벡터DB에 들어가고, 원본 구조는
어디에도 남지 않기 때문입니다.

이 상태에서 학습 데이터를 만들려면 검색 전용 저장소인 ChromaDB를 역으로 긁어야 합니다.
문서 단위 추적도, 개정 시 정확한 갱신도 불가능합니다.

따라서 **지식 원천을 별도 계층으로 분리하는 것**이 학습·추론·API 확장의 공통 전제입니다.

---

## 2. 현재 상태 (실측)

코드를 직접 실행하여 확인한 사실만 기록합니다.

### 2.1 동작하는 것

| 기능 | 위치 | 비고 |
| :--- | :--- | :--- |
| HWP/HWPX 표 구조 파싱 | `src/parsers/hwpx_parser.py` | 셀 좌표·병합·열너비·배경색 추출 |
| HWP ➔ PDF 변환 | `src/utils/hwp_to_pdf.py` | rhwp 네이티브 렌더링, 품질 양호 |
| HWP ➔ DOCX 변환 | `src/utils/hwp_to_docx.py` | pdf2docx 레이아웃 복원 |
| 벡터 인덱싱 | `src/rag/indexer.py` | ChromaDB |
| 하이브리드 검색 | `src/rag/retriever.py` | Vector + BM25 |
| 문서 삭제 | REST / MCP / 웹 3경로 | ChromaDB 청크 + 원본 + 마크다운 |
| MCP 서버 | `src/mcp_server.py` | stdio |
| REST API | `src/api/server.py` | FastAPI |

### 2.2 없는 것

| 항목 | 확인 결과 |
| :--- | :--- |
| 지식 원천 저장소 | 없음. 파싱 결과는 청크로만 남음 |
| `doc_id` | 없음. 식별자는 파일명뿐 |
| 문서 체크섬 | 없음. 갱신 감지 불가 |
| 학습 데이터셋 계층 | **코드 0줄.** `DATASETS_DIR`은 선언·mkdir만 되고 미사용 |
| QA 생성 | 없음 |
| 추론(LLM) 계층 | 없음. 검색 결과만 반환 |
| 임베딩 공급자 추상화 | 없음 |

### 2.3 확인된 결함

**① 구조 데이터가 생산되고 버려집니다**

`HwpxParser`가 `blocks`(셀 병합·좌표 포함)를 내보내지만, 소비하는 곳은
`hwp_to_docx.py` 한 곳뿐이며 그마저도 표를 렌더링하지 않고 버립니다.
인덱서는 `markdown` 문자열만 사용합니다.

**② 재인덱싱 시 옛 청크가 남습니다**

```python
chunk_id = f"{source_file}_chunk_{idx}"   # upsert
```

20청크였던 문서를 12청크로 개정하면 **13~20번 옛 청크가 살아남아** 검색에 걸립니다.
`upsert`는 덮어쓸 뿐 초과분을 지우지 않습니다.

**③ 표가 청크 중간에서 잘립니다**

`RecursiveCharacterTextSplitter(chunk_size=800)`가 표를 분할하여,
헤더 행과 데이터 행이 분리된 무의미한 청크가 생성됩니다.

**④ 설정된 임베딩 모델이 무시됩니다**

`EMBEDDING_MODEL = "BAAI/bge-m3"`이 선언돼 있으나 참조하는 코드가 없습니다.
실제로는 ChromaDB 기본 임베딩이 쓰입니다.

**⑤ BM25가 독립 검색 축이 아닙니다**

BM25 코퍼스가 벡터 검색이 반환한 최대 20개 문서로 한정되어,
벡터가 놓친 문서는 키워드로도 회수되지 않습니다.

**⑥ 변환된 DOCX는 텍스트가 손상됩니다**

pdf2docx 경로 실측: 띄어쓰기 전면 소실(`대표자 정보` ➔ `대표자정보`),
라벨과 값이 다른 요소로 분리(`활동분야` 셀이 비고 체크박스가 별도 배치).

---

## 3. 설계 원칙

### 원칙 1 — 사람용 산출물과 기계용 지식을 분리한다

```
                   ┌─ [사람용] pdf2docx ➔ .docx    시각 재현 우선
HWP ─→ 파서 blocks ─┤
                   └─ [기계용] KnowledgeStore ➔ RAG / 학습   텍스트 무결성 우선
```

> **변환된 `.docx`를 다시 인덱싱하지 않습니다.**
> 띄어쓰기가 붙고 라벨-값 연결이 끊긴 텍스트가 지식과 학습 데이터를 오염시킵니다.
> `data/temp`에 변환 결과물이 쌓이므로, 폴더 일괄 인덱싱 시 실제로 사고가 납니다.

### 원칙 2 — 사실은 RAG, 문체는 학습

| 다루는 대상 | 수단 | 이유 |
| :--- | :--- | :--- |
| 사실 정보 (금액·일정·기준) | **RAG** | 문서 개정 시 즉시 반영, 출처 인용 가능 |
| 문체·서식·용어 | **파인튜닝** | 재학습 없이는 못 바꾸므로 잘 안 변하는 것만 |

**파인튜닝한 모델에서는 특정 지식을 삭제할 수 없습니다.** 재학습이 유일한 방법입니다.
따라서 개정 가능성이 있는 사실을 학습에 넣지 않습니다.

### 원칙 3 — 파생물은 언제든 재생성 가능해야 한다

```
KnowledgeStore (원천, 유일한 진실)
    ├── ChromaDB 인덱스     ← 삭제해도 재구축 가능
    ├── BM25 인덱스         ← 삭제해도 재구축 가능
    └── 학습 데이터셋        ← 삭제해도 재생성 가능
```

원본 파일 없이도 재구축되어야 합니다. 그래야 청킹 전략이나 임베딩 모델을
바꾸는 일이 현실적인 선택지가 됩니다.

---

## 4. 목표 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│ 입력: HWP / HWPX / PDF / PPTX / DOCX                             │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
                  ┌───────────────────┐
                  │   Parsers         │  blocks(구조화) + markdown
                  └─────────┬─────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  [1] KnowledgeStore                    │  data/knowledge/
        │  KnowledgeRecord + ContentBlock        │  doc_id · checksum
        │  = Single Source of Truth              │  버전 · 출처
        └───┬───────────────┬───────────────┬───┘
            ▼               ▼               ▼
   ┌────────────┐   ┌──────────────┐  ┌──────────────┐
   │ [2] 인덱싱  │   │ [3] 데이터셋  │  │ [5] 조회 API │
   │ 표 통짜청킹 │   │ 규칙 QA/SFT   │  │ 목록·상세     │
   │ Vector+BM25│   │ 출처 추적      │  │ 재인덱싱      │
   └─────┬──────┘   └──────┬───────┘  └──────────────┘
         │                 ▼
         │          ┌──────────────┐
         │          │ [4] 학습      │  LoRA / 임베딩
         │          └──────┬───────┘
         │                 │ 학습된 모델
         ▼                 ▼
   ┌──────────────────────────────────┐
   │ [6] 추론 (Agentic RAG)            │
   │ 검색 ➔ 근거 주입 ➔ 답변 ➔ 출처   │
   └──────────────┬───────────────────┘
                  ▼
   ┌──────────────────────────────────┐
   │ [7] 제공: REST │ MCP │ 웹 UI      │
   └──────────────────────────────────┘
```

---

## 5. 데이터 스키마

### 5.1 KnowledgeRecord (문서 단위)

```python
@dataclass
class KnowledgeRecord:
    doc_id: str                 # sha256(정규화 경로 + 내용)[:16] — 파일명 아님
    source_file: str
    source_path: str
    file_type: str              # hwp | hwpx | pdf | pptx | docx

    blocks: list[ContentBlock]
    markdown: str               # 표시·호환용

    checksum: str               # 원본 SHA-256 (갱신 감지)
    parsed_at: datetime
    engine_used: str            # 어떤 파서 경로로 추출됐는지
    parser_version: str         # 파서 개선 시 재파싱 대상 선별용

    category: str
    tags: list[str]
    is_template: bool           # 빈 양식 여부 (5.4 참조)
    fill_ratio: float           # 채워진 셀 비율
    metadata: dict
```

**`doc_id`를 파일명 대신 쓰는 이유** — 현재는 식별자가 파일명뿐이라
동명이인 파일이 구분되지 않고, 개명하면 기존 청크와 연결이 끊겨 고아 데이터가 남습니다.

**`parser_version`이 필요한 이유** — 실제로 파서 결함으로 표가 통째로 유실된 적이 있습니다.
이 필드가 있으면 "구버전 파서로 처리된 HWP만" 골라 재파싱할 수 있습니다.

### 5.2 ContentBlock / TableData

```python
@dataclass
class ContentBlock:
    block_id: str
    block_type: Literal["heading", "paragraph", "table", "list", "note"]
    text: str | None
    table: TableData | None
    page: int | None
    order: int

@dataclass
class TableData:
    row_count: int
    col_count: int
    cells: list[TableCell]      # 좌표 + 병합 + 내용
    col_widths: list[int | None]

@dataclass
class TableCell:
    row: int
    col: int
    row_span: int
    col_span: int
    text: str
    fill: str | None            # 배경색 (섹션 머리글 판별에 활용)
```

`HwpxParser`가 이미 이 형태에 가까운 dict를 생산합니다. 저장만 하면 됩니다.

### 5.3 병합 정보로 계층 복원 — 품질의 핵심

`col_span == col_count`인 셀은 **섹션 머리글**입니다. 이 신호로 평면 표를 트리로 되돌립니다.

```
대표자 정보 (col_span=10)          ← 섹션
  ├ 성명 | ___ | 생년월일 | ___
  └ 연락처 | ___ | 이메일 | ___
커뮤니티 정보 (col_span=10)        ← 섹션
  └ 활동분야 | □인문 □사회 … □과학 □기타
```

이를 근거로 청크를 문맥이 살아 있는 형태로 만듭니다.

```
[대표자 정보] 성명: (공란) / 생년월일: (공란)
```

> pdf2docx 결과물로는 이것이 **원리적으로 불가능**합니다.
> 라벨과 값이 서로 다른 요소로 분리되어 있어 연결 정보가 존재하지 않습니다.

### 5.4 양식 문서와 작성본 구분

실측: 지원신청서는 **239셀 중 96셀만 채워진 빈 양식**입니다.

| 유형 | 판별 | 학습 활용 |
| :--- | :--- | :--- |
| 양식(template) | `fill_ratio` 낮음 | "신청서에 어떤 항목을 쓰는가" — 구조 지식 |
| 작성본·공고 | `fill_ratio` 높음 | "지원금은 얼마인가" — 사실 QA |

구분하지 않으면 공란 셀에서 **답이 비어 있는 샘플이 대량 생성**됩니다.

### 5.5 DatasetSample (학습 데이터)

```python
@dataclass
class DatasetSample:
    sample_id: str
    task_type: str              # sft | qa | embedding_pair
    payload: dict

    # 출처 추적 (필수)
    doc_id: str
    block_ids: list[str]        # 다대다 — 여러 문서 기반 샘플 대응
    generated_by: str           # rule:table_qa | llm:claude-opus-5 | human
    generated_at: datetime
    parser_version: str
    reviewed: bool = False
```

`doc_id` + `block_ids`가 있어야 **문서 개정·삭제 시 해당 샘플만 정확히 회수**할 수 있습니다.

### 5.6 저장 레이아웃

```
data/knowledge/
├── records/{doc_id}.json       # KnowledgeRecord
├── originals/{doc_id}{ext}     # 원본 보관 (재파싱 대비)
└── index.jsonl                 # 경량 목록 (doc_id, 파일명, checksum, 갱신일)

data/datasets/{name}/
├── manifest.json               # 생성 조건·소스 doc_id 목록·통계
├── train.jsonl
├── valid.jsonl
├── rejected.jsonl              # 품질 필터 탈락분 (필터 검증용)
└── index/by_doc.json           # doc_id ➔ sample_id 역인덱스
```

`by_doc.json`이 "문서별 QA 일괄 삭제"를 가능하게 하는 실체입니다.

외부 DB 없이 JSON/JSONL로 시작합니다. 수만 건을 넘어가면 SQLite로 바꾸되
`KnowledgeStore` 인터페이스는 유지하므로 호출부 수정이 필요 없습니다.

---

## 6. 단계별 구현

### Phase 0 — 즉시 수정 (반나절)

| # | 작업 | 대상 |
| :--- | :--- | :--- |
| 0-1 | 재인덱싱 전 `delete_document()` 호출 (잔여 청크 제거) | `src/rag/indexer.py` |
| 0-2 | 인덱싱 입력에서 변환 산출물(`.docx`, `_temp_pdf/`) 제외 가드 | `src/api/server.py`, `src/mcp_server.py` |
| 0-3 | DOCX 폴백이 표를 버리는 버그 수정 | `src/utils/hwp_to_docx.py` |

0-1은 **지금도 잘못된 검색 결과를 만들고 있으므로** 최우선입니다.

### Phase 1 — KnowledgeStore (핵심)

| # | 작업 | 산출물 |
| :--- | :--- | :--- |
| 1-1 | 스키마 정의 | `src/knowledge/schema.py` |
| 1-2 | JSON 스토어 (`put`/`get`/`list`/`delete`/`is_stale`) | `src/knowledge/store.py` |
| 1-3 | `HwpxParser` blocks ➔ `ContentBlock` 매핑 | `src/parsers/hwpx_parser.py` |
| 1-4 | `PdfParser` 표 추출(`find_tables`) 추가 | `src/parsers/pdf_parser.py` |
| 1-5 | `PptxParser` 블록화 | `src/parsers/pptx_parser.py` |
| 1-6 | 인덱싱 경로를 스토어 경유로 전환 | `src/rag/indexer.py` |
| 1-7 | 기존 HWP 문서 전량 재파싱·재인덱싱 | 운영 작업 |

### Phase 2 — 검색 품질

| # | 작업 | 산출물 |
| :--- | :--- | :--- |
| 2-1 | 표 통짜 청킹 + 섹션 머리글 문맥 부착 | `src/rag/chunker.py` |
| 2-2 | `EmbeddingProvider` 추상화 (`EMBEDDING_MODEL` 실제 사용) | `src/embeddings/` |
| 2-3 | 임베딩 차원 불일치 감지 | `src/rag/indexer.py` |
| 2-4 | BM25 독립 인덱스 (전체 코퍼스, 영속화) | `src/rag/sparse.py` |
| 2-5 | RRF 순위 융합으로 교체 | `src/rag/fusion.py` |

### Phase 3 — 학습 데이터셋

| # | 작업 | 산출물 |
| :--- | :--- | :--- |
| 3-1 | `DatasetSample` 스키마 + 역인덱스 | `src/training/schema.py` |
| 3-2 | **규칙 기반 표➔QA 빌더 (LLM 불필요)** | `src/training/builders/table_qa.py` |
| 3-3 | 품질 필터 (공란 셀 배제, 근거 포함 검증, 중복 제거) | `src/training/filters.py` |
| 3-4 | **문서 단위** train/valid 분할 | `src/training/split.py` |
| 3-5 | 문서 개정·삭제 시 샘플 회수 | `src/training/sync.py` |
| 3-6 | LLM 기반 SFT 빌더 | `src/training/builders/sft.py` |

**3-2를 3-6보다 먼저 하는 이유** — LLM 호출 없이 즉시 검증되고, 비용이 들지 않으며,
환각이 원천적으로 없습니다. 표만으로도 실용적인 데이터셋이 나옵니다.

```
표: | 항목 | 배점 |
    | 주제성/타당성 | 20 |
➔ Q: "주제성/타당성의 배점은?"  A: "20점"
```

### Phase 4 — 학습 실행 (선택 의존성)

| # | 작업 | 산출물 |
| :--- | :--- | :--- |
| 4-1 | `ExportOnlyRunner` (JSONL 내보내기, 기본값) | `src/training/runners/export.py` |
| 4-2 | 임베딩 파인튜닝 러너 | `src/training/runners/embedding.py` |
| 4-3 | LoRA 러너 | `src/training/runners/lora.py` |

torch·peft·trl은 무겁고 GPU 종속적이므로 핵심 의존성에 넣지 않습니다.

```toml
[project.optional-dependencies]
training = ["torch", "transformers", "peft", "trl", "sentence-transformers"]
```

### Phase 5 — 추론 계층

현재는 검색 결과만 반환하고 **답변을 생성하지 않습니다.**

| # | 작업 | 산출물 |
| :--- | :--- | :--- |
| 5-1 | LLM 공급자 추상화 (기본 `claude-opus-5`) | `src/inference/llm.py` |
| 5-2 | 근거 주입 답변 생성 + 출처 표기 | `src/inference/answer.py` |
| 5-3 | 근거 부족 시 재검색 루프 | `src/inference/agentic.py` |
| 5-4 | 환각 검증 (답변 근거가 청크에 실재하는지) | `src/inference/verify.py` |

### Phase 6 — API 제공

Phase 1~5의 기능을 REST와 MCP에 **동일하게** 노출합니다.

지금은 변환·검색 로직이 REST 핸들러와 MCP 핸들러에 중복 구현돼 있으므로,
먼저 서비스 계층으로 정리합니다.

```
src/services/{conversion,knowledge,dataset,inference}_service.py
        ▲                    ▲
   src/api/server.py    src/mcp_server.py
```

---

## 7. API 명세

### 7.1 지식 관리

| 메서드 | 경로 | MCP 도구 | 기능 |
| :--- | :--- | :--- | :--- |
| POST | `/api/knowledge` | `index_document` | 문서 등록 (파싱 ➔ 스토어 ➔ 인덱싱) |
| GET | `/api/knowledge` | `list_knowledge` | 목록 (category·file_type 필터) |
| GET | `/api/knowledge/{doc_id}` | `get_knowledge` | 구조화 내용 조회 |
| DELETE | `/api/knowledge/{doc_id}` | `delete_document` | 스토어·인덱스·데이터셋 샘플 연쇄 삭제 |
| POST | `/api/knowledge/{doc_id}/reindex` | `reindex` | 재인덱싱 |
| GET | `/api/knowledge/stale` | `check_stale` | 재파싱 필요 문서 목록 |

> 현재 삭제는 파일명 기준(`DELETE /api/documents/{filename}`)입니다.
> `doc_id` 기준으로 옮기되, 기존 경로는 한동안 유지하여 호환을 지킵니다.

### 7.2 데이터셋

| 메서드 | 경로 | MCP 도구 | 기능 |
| :--- | :--- | :--- | :--- |
| POST | `/api/datasets` | `build_dataset` | 생성 (task_type·필터 지정) |
| GET | `/api/datasets` | `list_datasets` | 목록 및 통계 |
| GET | `/api/datasets/{name}/manifest` | `get_dataset_manifest` | 생성 조건·소스 문서 |
| DELETE | `/api/datasets/{name}/documents/{doc_id}` | — | **문서별 샘플 선별 삭제** |
| POST | `/api/datasets/{name}/sync` | — | 개정 문서 샘플 증분 재생성 |

### 7.3 추론

| 메서드 | 경로 | MCP 도구 | 기능 |
| :--- | :--- | :--- | :--- |
| POST | `/api/search` | `search_knowledge` | 검색 (현행 유지) |
| POST | `/api/ask` | `ask_knowledge` | **근거 기반 답변 생성 + 출처** |

응답 예시:

```json
{
  "answer": "1팀당 70만원이며 별도의 정산은 없습니다.",
  "sources": [
    {"doc_id": "hwp_a91c...", "source_file": "AI 커뮤니티 활동지원 모집공고.hwp",
     "block_id": "tbl1_r4", "quote": "커뮤니티 활동지원금 1팀당 70만원"}
  ],
  "confidence": 0.86
}
```

---

## 8. 주의사항

### 8.1 학습한 모델에서는 지식을 삭제할 수 없습니다

```
데이터셋에서 삭제            ✅ 가능 (by_doc.json 역인덱스)
파인튜닝된 모델 가중치에서 삭제  ❌ 불가능 — 재학습만이 방법
```

문서가 개정·폐기돼도 이미 학습한 모델은 옛 정보를 계속 말합니다.
**개정 가능성이 있는 사실은 학습에 넣지 말고 RAG로 다루십시오.** (원칙 2)

### 8.2 여러 문서에서 생성된 샘플

문서 간 비교 QA는 `doc_id`가 복수입니다. 한쪽 문서를 지울 때
샘플을 삭제할지 재생성할지 정책이 필요합니다. `block_ids`를 다대다로 설계하는 이유입니다.

### 8.3 데이터 분할 누수

train/valid는 반드시 **문서 단위**로 나눕니다. 청크 단위로 나누면 같은 문서의
조각이 양쪽에 들어가 성능이 과대평가됩니다. 증분 갱신 시에도 분할이 유지되어야 합니다.

### 8.4 재생성은 "삭제 후 삽입"

`upsert`만으로는 초과분이 남습니다(2.3 ②). 인덱스든 데이터셋이든
**기존 삭제 ➔ 신규 삽입**을 원칙으로 강제합니다.

### 8.5 외부 노출 시 보안

현재 REST는 인증이 없고 CORS가 전면 개방(`allow_origins=["*"]`)이며,
`/api/convert_folder`가 임의 경로를 읽고 씁니다.
로컬 단독 사용은 무방하나 **외부 노출 전 API Key·CORS 제한·경로 화이트리스트가 필수**입니다.

---

## 9. 검증 기준

### Phase 1

- [ ] `.hwp` 등록 시 `records/{doc_id}.json`에 병합 정보를 가진 표가 저장된다
- [ ] ChromaDB를 통째로 지워도 **원본 파일 없이** 스토어만으로 전량 재인덱싱된다
- [ ] 동일 문서를 두 번 등록해도 `checksum` 비교로 중복 처리되지 않는다
- [ ] 파일명이 같고 경로가 다른 두 문서가 서로 다른 `doc_id`를 갖는다
- [ ] REST와 MCP 경로가 동일한 저장 결과를 만든다

### Phase 2

- [ ] 표가 청크 중간에서 잘리지 않는다
- [ ] 청크에 섹션 머리글 문맥이 붙는다 (`[대표자 정보] 성명: …`)
- [ ] 개정으로 청크 수가 줄면 **옛 청크가 남지 않는다**
- [ ] `EMBEDDING_MODEL` 설정이 실제 임베딩에 반영된다
- [ ] "공고 제96호" 같은 고유 문자열을 BM25 축이 독립 회수한다
- [ ] 임베딩 모델 교체 시 차원 불일치가 명시적 오류로 감지된다

### Phase 3

- [ ] LLM 호출 없이 표에서 QA 샘플이 생성된다
- [ ] 모든 샘플이 `doc_id`/`block_ids`로 원본까지 역추적된다
- [ ] 빈 양식의 공란 셀에서 무의미한 샘플이 생성되지 않는다
- [ ] **문서 하나를 삭제하면 그 문서에서 나온 샘플만 정확히 제거된다**
- [ ] train/valid가 문서 단위로 분할되어 누수가 없다
- [ ] 학습 프레임워크 미설치 상태에서도 데이터셋 생성이 동작한다

### Phase 5~6

- [ ] `/api/ask`가 근거 인용과 함께 답변한다
- [ ] 근거에 없는 내용을 답하면 환각 검증에 걸린다
- [ ] 동일 로직이 REST/MCP에 중복 구현되어 있지 않다

---

## 10. 착수 순서 요약

```
[Phase 0] 즉시 수정        ← 잘못된 검색 결과를 지금 만들고 있음
    ▼
[Phase 1] KnowledgeStore   ← 없으면 이후 전부가 벡터DB에 종속됨
    ├──────────────┬──────────────┐
    ▼              ▼              ▼
[Phase 2]      [Phase 3]      [Phase 6]
검색 품질       데이터셋        API 정리
    │              ▼
    │          [Phase 4] 학습
    └──────────────┴──────────────┐
                                  ▼
                            [Phase 5] 추론
```

**Phase 1을 최우선으로 두는 이유**: 이것이 없으면 데이터셋 빌더도, 조회 API도
ChromaDB를 직접 참조하게 되어, 나중에 저장소를 바꾸거나 학습을 붙일 때
전면 재작성이 필요해집니다.

---

## 관련 문서

- **[02. 기술 선택 및 인터페이스 명세](./02_technology_stack_and_interfaces.md)** — 본 문서의 짝.
  어떤 임베딩 모델·저장소·LLM·프로토콜을 쓸 것인지와 그 근거
- **[03. 한국어 임베딩 모델 조사 및 선정](./03_korean_embedding_model_evaluation.md)** —
  리더보드 조사, 후보 비교, 자체 평가 방법
- **[04. 지식을 학습 데이터로 만드는 방법](./04_knowledge_to_training_data.md)** —
  무엇을 학습시키고 무엇을 학습시키지 않을 것인가, 다중 문서 처리, ML/DL 경로
- [고도화 로드맵 총괄](../advancement/00_advancement_roadmap.md)
- [현행 시스템 실측 감사](../advancement/01_current_state_audit.md) — 본 문서 2절의 상세 근거
- [지식 추상화 계층 설계](../advancement/02_knowledge_store_abstraction.md)
- [임베딩·검색 공급자 추상화](../advancement/03_embedding_provider_abstraction.md)
- [ML/DL 학습 데이터 계층](../advancement/04_ml_dl_dataset_and_training.md)
