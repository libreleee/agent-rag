# 02. 지식 추상화 계층 (KnowledgeStore)

> **선행 의존성**: [01_current_state_audit.md](./01_current_state_audit.md)
> **후행 작업**: 03(임베딩 공급자), 04(학습 데이터), 05(A2A) — 모두 본 문서에 의존

---

## 1. 현재 상태 (As-Is)

파싱 결과는 곧바로 청킹되어 ChromaDB로 들어가고, 그 외에는 어디에도 남지 않습니다.

```
파서 ──> parsed_data{"markdown": "..."} ──> RecursiveCharacterTextSplitter
                                                      │
                                                      ▼
                                          ChromaDB.upsert(청크 텍스트)
```

`src/rag/indexer.py`가 저장하는 메타데이터는 다음이 전부입니다.

```python
meta = {
    "source_file": source_file,
    "file_type": file_type,
    "chunk_index": idx,
    "total_chunks": len(chunks),
}
```

`/api/upload` 경로에서만 파싱 마크다운을 `data/processed/*.md`로 따로 저장하지만
(`src/api/server.py`), MCP `index_document` 경로에는 이 저장이 없어 **경로에 따라
보존 여부가 달라집니다.** 또한 이 `.md` 파일은 스키마 없는 평문이라 프로그램적으로
활용하기 어렵습니다.

### 이 구조의 문제

| 문제 | 결과 |
| :--- | :--- |
| 원본 구조 미보존 | 표를 표로서 다룰 수 없음 (마크다운 문자열로만 존재) |
| 청킹 결과만 저장 | 청킹 전략 변경 시 **원본 파일부터 전량 재파싱** |
| 버전/체크섬 없음 | 문서 갱신 감지 불가, 중복 인덱싱 방지 불가 |
| 출처 위치 없음 | 답변의 근거를 "몇 페이지 어느 표"로 특정 불가 |
| 벡터DB가 유일 저장소 | 학습 데이터 추출 시 검색 전용 저장소를 역으로 조회해야 함 |
| 경로별 동작 불일치 | REST는 `.md` 저장, MCP는 미저장 |

01번 문서 2.6절에서 확인된 **"HWP 전량 재인덱싱 필요"** 상황이 곧 이 문제의 실증입니다.
원본 파일을 다시 찾아 처음부터 파싱하는 것 외에 방법이 없습니다.

---

## 2. 목표 상태 (To-Be)

파싱과 인덱싱 사이에 **정규화된 지식 원천 계층**을 삽입합니다.

```
파서 ──> KnowledgeRecord ──> KnowledgeStore (data/knowledge/)
                                   │  = Single Source of Truth
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   RAG 인덱서                 DatasetBuilder            A2A / MCP 조회
   (재구축 가능)               (학습 데이터)              (지식 열람)
```

핵심 원칙: **ChromaDB는 파생물이며 언제든 KnowledgeStore로부터 재구축 가능해야 합니다.**

---

## 3. 데이터 스키마 정의

### 3.1 KnowledgeRecord (문서 단위)

```python
@dataclass
class KnowledgeRecord:
    # 식별
    doc_id: str                 # 안정적 ID (경로+내용 해시 기반)
    source_file: str            # 원본 파일명
    source_path: str            # 원본 절대경로
    file_type: str              # hwp / hwpx / pdf / pptx / docx

    # 내용
    blocks: list[ContentBlock]  # 구조화된 본문 블록 (아래 3.2)
    markdown: str               # 렌더링된 전체 마크다운 (호환/표시용)

    # 출처 및 이력
    checksum: str               # 원본 파일 SHA-256 (갱신 감지용)
    parsed_at: datetime
    engine_used: str            # 어떤 파서 경로로 추출됐는지
    parser_version: str         # 파서 로직 버전 (재파싱 필요 판단용)

    # 분류
    category: str               # 규정 / 매뉴얼 / 공고 / 보고서 ...
    tags: list[str]
    metadata: dict              # 부서, 보안등급, 유효기간 등 확장 필드
```

`engine_used`와 `parser_version`을 함께 남기는 이유는 실무적입니다.
01번 문서에서 확인했듯 **파서 결함으로 이미 인덱싱된 문서가 오염될 수 있습니다.**
이 두 필드가 있으면 "구버전 파서로 처리된 HWP만 골라 재파싱"이 가능해집니다.

### 3.2 ContentBlock (블록 단위)

마크다운 문자열이 아니라 **타입이 있는 블록**으로 보존하는 것이 핵심입니다.

```python
@dataclass
class ContentBlock:
    block_id: str
    block_type: Literal["heading", "paragraph", "table", "list", "note", "image"]
    text: str | None            # 텍스트 블록의 내용
    table: TableData | None     # 표 블록의 2D 구조
    level: int | None           # heading 레벨
    page: int | None            # 출처 페이지
    section: str | None         # 출처 섹션
    order: int                  # 문서 내 순서
```

```python
@dataclass
class TableData:
    rows: list[list[str]]                  # 2D 셀 매트릭스
    header_row: int | None                 # 헤더 행 인덱스 (없으면 None)
    merges: list[tuple[int, int, int, int]]  # 병합 셀 (r, c, rowspan, colspan)
    caption: str | None
```

**표를 `TableData`로 보존해야 하는 이유:**

- 표 전체를 하나의 청크로 유지하여 행이 잘리는 것을 방지 (RAG 정확도 직결)
- 학습 데이터 생성 시 "이 표의 X 항목 값은?" 형태의 QA를 **기계적으로** 생성 가능
- 마크다운/Word/JSON 어느 포맷으로든 무손실 재출력 가능
- 01번 문서 2.7절의 병합 셀 문제를 표현할 자리가 생김

### 3.3 저장 레이아웃

```
data/knowledge/
├── records/
│   └── {doc_id}.json          # KnowledgeRecord 직렬화
├── originals/
│   └── {doc_id}{ext}          # 원본 파일 보관 (재파싱 대비)
└── index.jsonl                # 전체 레코드 요약 (빠른 목록 조회)
```

`index.jsonl`은 `doc_id`, `source_file`, `category`, `checksum`, `parsed_at`,
`block_count`만 담는 경량 목록으로, 전체 레코드를 로드하지 않고 스캔할 수 있게 합니다.

**저장 포맷으로 JSON/JSONL을 선택한 이유**: 외부 DB 의존성 없이 시작할 수 있고,
`git diff`로 변경 추적이 가능하며, 학습 파이프라인이 곧바로 읽을 수 있습니다.
문서 수가 수만 건을 넘어가면 SQLite로 전환하되, `KnowledgeStore` 인터페이스는
그대로 유지되므로 호출부 수정은 불필요합니다.

---

## 4. 인터페이스 정의

```python
class KnowledgeStore(Protocol):
    def put(self, record: KnowledgeRecord) -> str:
        """레코드 저장 후 doc_id 반환. 동일 doc_id 존재 시 갱신."""

    def get(self, doc_id: str) -> KnowledgeRecord | None: ...

    def list(
        self,
        category: str | None = None,
        file_type: str | None = None,
        tags: list[str] | None = None,
        parser_version: str | None = None,
    ) -> list[KnowledgeRecordSummary]:
        """조건에 맞는 레코드 요약 목록. DatasetBuilder와 재인덱싱이 이 메서드를 사용."""

    def delete(self, doc_id: str) -> bool: ...

    def is_stale(self, source_path: str) -> bool:
        """원본 체크섬 또는 parser_version 비교로 재파싱 필요 여부 판단."""

    def iter_blocks(
        self, doc_id: str, block_types: list[str] | None = None
    ) -> Iterator[ContentBlock]:
        """블록 단위 순회. 예: 표만 뽑아 학습 데이터 생성."""
```

`is_stale()`이 중요합니다. 이것이 있어야 배치 인덱싱 시
**변경된 문서만 골라 처리**하고, 파서를 개선했을 때 영향받는 문서만 재처리할 수 있습니다.

---

## 5. 파서 계약 변경

현재 파서들은 `{"markdown": str, ...}` 딕셔너리를 반환합니다.
이를 `ContentBlock` 리스트를 함께 반환하도록 확장합니다.

```python
# 변경 전
{"source_file": ..., "file_type": ..., "markdown": "...", "char_count": N}

# 변경 후 (기존 키 유지 = 하위 호환)
{
    "source_file": ..., "file_type": ..., "markdown": "...", "char_count": N,
    "blocks": [ContentBlock, ...],      # 신규
    "engine_used": ..., "parser_version": ...,
}
```

기존 키를 그대로 두면 `hwp_to_docx.py`, `api/server.py` 등 호출부를 건드리지 않고
점진적으로 이행할 수 있습니다.

**파서별 작업량:**

| 파서 | 작업 | 난이도 |
| :--- | :--- | :--- |
| `HwpxParser` | 이미 표를 2D 매트릭스로 복원 중 ➔ `TableData`로 내보내면 됨 | 낮음 |
| `HwpDualEngineParser` | `HwpxParser` 결과를 그대로 위임 | 낮음 |
| `PdfParser` | 현재 `page.get_text("text")`만 사용. PyMuPDF `find_tables()` 추가 필요 | 중간 |
| `PptxParser` | 슬라이드/노트 단위 블록화 | 중간 |

`HwpxParser`가 이미 `_parse_table_to_markdown()`에서 2D 매트릭스를 만들고 있으므로
(`table_matrix` 변수), 마크다운으로 조립하기 **직전 단계의 매트릭스**를 그대로
`TableData.rows`에 넣으면 됩니다. 추가 파싱 로직이 필요 없습니다.

---

## 6. 인덱서 변경

`KnowledgeIndexer`가 파싱 결과가 아닌 **KnowledgeRecord를 입력받도록** 변경합니다.

```python
def index_record(self, record: KnowledgeRecord) -> int:
    for block in record.blocks:
        if block.block_type == "table":
            # 표는 분할하지 않고 통째로 하나의 청크로 (행 잘림 방지)
            chunks = [render_table_as_markdown(block.table)]
        else:
            chunks = self.text_splitter.split_text(block.text)

        for chunk in chunks:
            meta = {
                "doc_id": record.doc_id,
                "source_file": record.source_file,
                "block_id": block.block_id,     # 출처 역추적
                "block_type": block.block_type,
                "page": block.page,
                "category": record.category,
            }
            ...
```

**표를 분할하지 않는 것이 핵심 개선**입니다. 현재는 `RecursiveCharacterTextSplitter`가
800자 단위로 자르므로 큰 표는 중간에서 잘려 헤더 행과 데이터 행이 분리됩니다.
그 상태로 검색되면 어떤 열의 값인지 알 수 없는 무의미한 청크가 반환됩니다.

또한 `block_id`를 메타데이터에 남기면 검색 결과에서 **"이 답변은 3페이지 심사기준표에서
나왔다"** 는 출처 추적이 가능해집니다.

---

## 7. 신규 노출 도구

KnowledgeStore가 생기면 MCP/REST에 다음 도구를 추가합니다.

| 도구 | 용도 |
| :--- | :--- |
| `list_knowledge(category, file_type)` | 등록된 지식 목록 조회 |
| `get_knowledge(doc_id)` | 특정 문서의 구조화 내용 조회 |
| `reindex(doc_id \| all, force)` | 재인덱싱 (파서 개선 후 사용) |
| `check_stale()` | 재파싱 필요 문서 목록 |

`reindex`와 `check_stale`은 01번 문서 2.6절의 **HWP 전량 재인덱싱** 상황을
운영 중에 처리하기 위해 필요합니다.

---

## 8. 작업 항목

| # | 작업 | 산출물 | 선행 |
| :--- | :--- | :--- | :--- |
| 1 | 스키마 정의 | `src/knowledge/schema.py` | - |
| 2 | JSON 기반 스토어 구현 | `src/knowledge/store.py` | 1 |
| 3 | `HwpxParser` 블록 출력 | `src/parsers/hwpx_parser.py` | 1 |
| 4 | `PdfParser` 표 추출 추가 | `src/parsers/pdf_parser.py` | 1 |
| 5 | `PptxParser` 블록 출력 | `src/parsers/pptx_parser.py` | 1 |
| 6 | 인덱서를 레코드 기반으로 전환 | `src/rag/indexer.py` | 2, 3 |
| 7 | REST/MCP에 조회·재인덱싱 도구 추가 | `src/api/server.py`, `src/mcp_server.py` | 2, 6 |
| 8 | 기존 HWP 문서 전량 재파싱·재인덱싱 | (운영 작업) | 7 |

**8번은 반드시 마지막에 수행합니다.** 01번 문서에서 수정한 파서로 다시 파싱해야
표가 포함된 정상 데이터가 KnowledgeStore에 적재됩니다.

---

## 9. 완료 판정 기준

- [ ] `.hwp` 인덱싱 후 `data/knowledge/records/*.json`에 `TableData`가 포함된다
- [ ] ChromaDB를 삭제해도 KnowledgeStore만으로 **원본 파일 없이** 전량 재인덱싱된다
- [ ] 검색 결과 메타데이터로 출처 블록(페이지/표)을 특정할 수 있다
- [ ] 동일 문서를 두 번 인덱싱해도 `checksum` 비교로 중복 처리되지 않는다
- [ ] 표가 청크 중간에서 잘리지 않는다
- [ ] REST와 MCP 경로가 동일한 저장 결과를 만든다
