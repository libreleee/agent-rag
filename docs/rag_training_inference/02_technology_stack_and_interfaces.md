# 기술 선택 및 인터페이스 명세

**"무엇을 쓸 것인가"** 를 정하는 문서입니다.
[01_knowledge_training_inference_api_spec.md](./01_knowledge_training_inference_api_spec.md)가
아키텍처와 구현 단계를 다룬다면, 본 문서는 각 계층에 어떤 모델·저장소·프로토콜을 쓸지와
그 근거를 기록합니다.

모든 현행 상태는 **실제로 설치·실행하여 확인한 값**입니다.

작성 기준일: 2026-08-17

---

## 0. 가장 먼저 정리할 개념 — RAG는 추론이 아닙니다

```
[질문]
   │
   ▼
[RAG · 검색]  근거가 될 청크를 찾아온다        ◀── 현재 여기까지만 구현됨
   │
   ▼
[LLM · 추론]  찾아온 근거로 답변을 생성한다     ◀── 이 계층이 통째로 없음
   │
   ▼
[답변 + 출처]
```

RAG는 **근거를 찾는 일**이고, 추론은 **그 근거로 답을 만드는 일**입니다.
현재 `/api/search`는 검색된 청크 목록만 반환하며 답변을 생성하지 않습니다.
LLM SDK도 설치되어 있지 않습니다.

> **"RAG만 붙이면 추론이 된다"는 성립하지 않습니다.**
> 추론 계층은 별도로 만들어야 합니다.

---

## 1. 임베딩 모델

### 1.1 현행 (실측)

| 항목 | 확인 결과 |
| :--- | :--- |
| 실제 동작 중인 임베딩 | ChromaDB 기본 임베딩 — **384차원** (all-MiniLM 계열, ONNX 실행) |
| 설정 파일의 선언 | `EMBEDDING_MODEL = "BAAI/bge-m3"` — **코드 어디서도 참조되지 않음** |
| `sentence-transformers` | **미설치** |
| `torch` | **미설치** |
| `onnxruntime` | 설치됨 (ChromaDB 의존성) |

즉 `config.py`를 읽은 사람이 기대하는 성능과 실제 성능이 다릅니다.
384차원 MiniLM 계열은 한국어 성능이 bge-m3보다 뚜렷하게 떨어집니다.

### 1.2 선택 (2026년 8월 기준 조사)

> 리더보드 원자료, 후보 비교, **자체 평가 방법**은
> **[03. 한국어 임베딩 모델 조사 및 선정](./03_korean_embedding_model_evaluation.md)** 에 있습니다.
> 아래는 그 결론만 옮긴 것입니다.

한국어 MTEB 리더보드(NDCG@5,10 평균) 상위권입니다.

| 순위 | 모델 | 점수 | 비고 |
| :--- | :--- | :--- | :--- |
| 1 | `perplexity-ai/pplx-embed-v1-4b` | 82.79 | 4B — 무겁고 라이선스 확인 필요 |
| 2 | **`dragonkue/snowflake-arctic-embed-l-v2.0-ko`** | **82.14** | **0.6B · 1024차원 · 8192토큰 · Apache-2.0** |
| 3 | `telepix/PIXIE-Rune-v1.0` | 81.57 | |

**권장: `dragonkue/snowflake-arctic-embed-l-v2.0-ko`**

| 근거 | 내용 |
| :--- | :--- |
| 성능 | 한국어 리더보드 2위이면서 1위보다 **6배 이상 가벼움**(0.6B vs 4B) |
| bge-m3 대비 | 제작자 보고 기준 평균 NDCG@10 **0.7404 vs 0.7242** — 특히 XPQA(0.444 vs 0.361), AutoRAG(0.909 vs 0.830)에서 우위 |
| 라이선스 | **Apache-2.0** — 상업적 이용·수정·배포 자유 |
| 차원 | **1024** — bge-m3와 동일하므로 인덱스 차원 설계가 같음 |
| 문맥 | 8192 토큰 — 긴 공문·규정 문서에 유리 |

**대안 선택지**

| 모델 | 언제 쓰나 |
| :--- | :--- |
| `BAAI/bge-m3` | 여전히 견고한 선택. **Dense + Sparse를 한 모델로** 처리하고 싶을 때 (아래 1.5 참조). MIT |
| `nlpai-lab/KURE-v1` | bge-m3 기반 한국어 특화 파인튜닝. 별도 리더보드에서 상위 |
| ChromaDB 기본 | 설정을 바꾸지 않았을 때의 현행 동작 (384차원, 한국어 취약) |

> **주의**: 리더보드마다 평가 데이터셋과 지표가 달라 **점수를 교차 비교하면 안 됩니다.**
> 위 표는 같은 리더보드 안에서의 상대 순위입니다. 최종 선택 전에 자사 문서
> (예: 성남시 공고문·신청서)로 자체 평가를 돌리는 것을 권장합니다.

### 1.5 Dense와 Sparse를 한 모델로 할 것인가

`bge-m3`는 한 모델에서 Dense와 Sparse(어휘) 벡터를 함께 내놓습니다.
반면 `arctic-embed-l-v2.0-ko`는 **Dense 전용**입니다.

| 구성 | 조합 | 비고 |
| :--- | :--- | :--- |
| **A (권장)** | `arctic-embed-ko` (Dense) + **BM25** (Sparse) | 두 축이 완전히 독립. 본 프로젝트 설계와 일치 |
| B | `bge-m3` 단독 (Dense + Sparse) | 모델 하나로 단순하나 Dense 성능이 A보다 낮음 |
| C | `arctic-embed-ko` + **한국어 SPLADE** | Sparse도 학습 모델로 대체 (아래) |

**C안 참고** — 같은 리더보드의 Sparse 부문 상위:

| 모델 | 점수 |
| :--- | :--- |
| `telepix/PIXIE-Splade-v1.5` | 78.19 |
| `yjoonjang/splade-ko-v1` | 77.00 |

BM25는 조사가 붙는 한국어 특성상 형태소 분석 없이는 매칭률이 떨어집니다.
SPLADE 계열은 이를 학습으로 해결하지만 인덱싱 비용이 큽니다.
**A안으로 시작하고, BM25의 한국어 한계가 실제로 문제가 될 때 C안을 검토**하십시오.

### 1.3 중요 — Claude API에는 임베딩 엔드포인트가 없습니다

Claude API가 제공하는 엔드포인트는 Messages, Batches, Files, Models, Token Counting입니다.
**임베딩 엔드포인트는 없습니다.**

따라서 구성은 다음과 같이 나뉩니다.

```
LLM 추론  ──> Claude (claude-opus-5)
임베딩    ──> 로컬 모델 (bge-m3) 또는 별도 임베딩 공급자
```

이 둘을 한 공급자로 묶으려 하면 안 됩니다.

### 1.4 차원 변경 시 주의

384차원 ➔ 1024차원으로 바꾸면 **기존 인덱스와 호환되지 않습니다.**
반드시 전량 재인덱싱이 필요하며, 이를 런타임에 감지해야 합니다.

```python
collection = client.get_or_create_collection(
    name="enterprise_knowledge",
    metadata={"embedding_provider": provider.name, "dimension": provider.dimension},
)
# 불일치 시 조용한 오작동 대신 명시적 오류 + 재인덱싱 안내
```

> KnowledgeStore가 있으면 재인덱싱이 값싼 작업이 되므로, 모델 교체가
> 비로소 현실적인 선택지가 됩니다. 이것이 지식 원천 계층을 선행시키는 이유 중 하나입니다.

---

## 2. 데이터베이스 — 하나로 다 하려 하지 마십시오

### 2.1 3종 저장소

| 저장소 | 역할 | 선택 | 교체 가능성 |
| :--- | :--- | :--- | :--- |
| **지식 원천** | `KnowledgeRecord` 정본 | JSON/JSONL → 수만 건 초과 시 SQLite | 인터페이스 뒤에 있어 자유 |
| **벡터 인덱스** | 의미 기반 검색 | ChromaDB (현행 유지) | 파생물이므로 재구축 가능 |
| **키워드 인덱스** | BM25 어휘 검색 | 파일 영속화 | 파생물 |

### 2.2 왜 나누는가

현재는 ChromaDB가 유일한 저장소입니다. 그 결과:

- 학습 데이터를 만들려면 **검색 전용 저장소를 역으로 긁어야** 합니다
- 청킹 전략을 바꾸면 **원본 파일부터 전량 재파싱**해야 합니다
- 문서 버전·갱신 감지·출처 추적이 불가능합니다

```
[올바른 관계]
KnowledgeStore (원천, 유일한 진실)
    ├── ChromaDB 인덱스   ← 지워도 재구축 가능
    ├── BM25 인덱스       ← 지워도 재구축 가능
    └── 학습 데이터셋      ← 지워도 재생성 가능
```

**벡터DB를 파생물로 강등하는 것**이 핵심입니다.

### 2.3 BM25 인덱스 현행 문제

`rank-bm25`는 설치되어 있고 코드도 존재하지만 두 가지 한계가 있습니다.

- BM25 코퍼스가 **벡터 검색이 반환한 20개 문서로 한정** → 독립 검색 축이 아님
- `BM25Okapi(...)`가 **질의마다 새로 생성** → 영속화 없음

전체 코퍼스를 대상으로 인덱스를 만들어 디스크에 보관해야 합니다.

---

## 3. 외부 인터페이스 4종

| 대상 | 프로토콜 | 현재 상태 |
| :--- | :--- | :--- |
| 타 정보시스템 (앱·백엔드) | **REST** (FastAPI) | 있음 — 인증 없음 |
| AI 에이전트 (도구 호출) | **MCP** (stdio) | 있음 — 도구 7개 |
| AI 에이전트 (작업 위임) | **A2A** | **없음** |
| 사람 | 웹 UI / 데스크톱 GUI | 있음 |

### 3.1 MCP와 A2A는 경쟁이 아니라 계층이 다릅니다

| 구분 | MCP | A2A |
| :--- | :--- | :--- |
| 관계 | 에이전트 ➔ **도구** | 에이전트 ➔ **에이전트** |
| 호출 | 동기적 함수 호출 | 태스크 위임 (장시간 실행) |
| 상태 | 무상태 | 태스크 수명주기 |
| 발견 | 설정에 사전 등록 | Agent Card로 런타임 발견 |

**둘 다 필요합니다.**

- "HWP를 PDF로 변환" → 즉시 끝나는 **도구 호출(MCP)**
- "이 폴더 문서로 학습 데이터셋을 만들어줘" → 수 분 걸리는 **작업 위임(A2A)**

데이터셋 생성이 A2A의 대표적인 대상입니다.

### 3.2 서비스 계층이 선행되어야 합니다

현재 변환·검색 로직이 MCP 핸들러와 REST 핸들러에 **중복 구현**되어 있습니다.
(`batch_convert_folder`와 `convert_folder_batch`가 거의 동일한 코드)

이 상태에서 A2A를 추가하면 **같은 로직이 세 벌**이 됩니다.

```
src/services/{conversion,knowledge,dataset,inference}_service.py
        ▲            ▲            ▲
   api/server.py  mcp_server.py  a2a/server.py     ← 모두 얇은 껍데기
```

### 3.3 보안 (외부 노출 시 필수)

현재 REST는 인증이 없고 CORS가 전면 개방(`allow_origins=["*"]`)이며,
`/api/convert_folder`가 임의 경로를 읽고 씁니다.

| 조치 | 시점 |
| :--- | :--- |
| API Key 인증 (`X-API-Key`) | 외부 노출 전 필수 |
| CORS 허용 출처 명시 | 외부 노출 전 필수 |
| 파일 경로 화이트리스트 | 외부 노출 전 필수 |
| 업로드 파일명 검증 | 권장 (현재 `file.filename` 무검증 사용) |

---

## 4. 학습 인터페이스 — 프레임워크를 품지 마십시오

### 4.1 구조

```
KnowledgeStore ──> DatasetBuilder ──> JSONL 내보내기 ──> [외부 환경에서 학습]
                                            ▲
                                       기본 경로
```

### 4.2 의존성 분리

`torch`, `peft`, `trl`은 무겁고 GPU 환경에 종속적입니다.
**핵심 의존성에 넣지 않습니다.**

```toml
[project.optional-dependencies]
training = ["torch", "transformers", "peft", "trl", "sentence-transformers"]
```

기본 러너(`ExportOnlyRunner`)는 **JSONL만 내보내고 종료**합니다.
이렇게 하면 학습 환경(사내 GPU 서버, Colab, 외부 플랫폼)을 자유롭게 선택할 수 있고,
학습 프레임워크 미설치 상태에서도 데이터셋 생성이 동작합니다.

### 4.3 규칙 기반 생성을 우선하십시오

표(`TableData`)에서 **LLM 호출 없이** QA를 기계적으로 생성할 수 있습니다.

```
| 항목 | 배점 |
| 주제성/타당성 | 20 |
➔ Q: "주제성/타당성의 배점은?"  A: "20점"
```

비용 0원, 환각 0건입니다. LLM 기반 합성 QA는 그 위에 서술형만 얹습니다.

---

## 5. 추론 인터페이스 (신설)

### 5.1 모델 선택

| 항목 | 선택 |
| :--- | :--- |
| 모델 | **`claude-opus-5`** |
| SDK | `anthropic` (Python) — **현재 미설치** |
| 사고 | `thinking={"type": "adaptive"}` |
| 긴 출력 | `client.messages.stream()` |

### 5.2 호출 형태

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    thinking={"type": "adaptive"},
    system=(
        "제공된 근거만 사용해 답변하십시오. "
        "근거에 없는 내용은 추측하지 말고 모른다고 답하십시오. "
        "각 주장마다 출처 block_id를 표기하십시오."
    ),
    messages=[{"role": "user", "content": prompt_with_context}],
)
```

**설정 근거**

- **adaptive thinking** — 여러 근거를 대조하고 상충을 판단하는 다단계 추론에 필요합니다.
- **스트리밍** — 긴 답변은 `messages.stream()`으로 HTTP 타임아웃을 피합니다.
- **프롬프트 캐싱** — 검색된 근거 블록에 `cache_control`을 걸면 같은 문서에
  이어서 질문할 때 비용이 크게 줄어듭니다.

### 5.3 LLM 공급자 추상화 — 클라우드와 로컬을 함께 지원합니다

임베딩과 마찬가지로 인터페이스 뒤에 둡니다.

```python
class LLMProvider(Protocol):
    name: str
    def generate(self, system: str, messages: list, **opts) -> LLMResponse: ...
    def stream(self, system: str, messages: list, **opts) -> Iterator[str]: ...
```

| 구현체 | 용도 |
| :--- | :--- |
| `ClaudeProvider` | 기본값. 최고 품질, 외부 전송 |
| `LocalOpenAICompatProvider` | **온프레미스 LLM** — 망분리·기밀 문서·비용 통제 |
| `FineTunedProvider` | 자체 학습 모델 투입 |

### 5.4 로컬 LLM 운용

**핵심: 대부분의 로컬 서빙 엔진이 OpenAI 호환 API를 노출합니다.**
따라서 구현체는 **하나면 충분**하고, 엔진은 설정으로 바꿉니다.

```
LocalOpenAICompatProvider ──HTTP──> vLLM | Ollama | llama.cpp
                                     (OpenAI 호환 /v1/chat/completions)
```

| 엔진 | 적합한 상황 |
| :--- | :--- |
| **vLLM** | 운영 환경. 처리량·동시성이 중요할 때 |
| **Ollama** | 개발·소규모. 설치와 모델 교체가 간편 |
| **llama.cpp** | GPU 없이 CPU/저사양에서 돌려야 할 때 |

```python
LLM_PROVIDER: str = "claude"                       # claude | local | finetuned
LLM_MODEL: str = "claude-opus-5"
LOCAL_LLM_BASE_URL: str | None = None              # 예: http://localhost:11434/v1
LOCAL_LLM_MODEL: str | None = None
```

**클라우드와 로컬을 함께 쓰는 방식**

| 방식 | 설명 |
| :--- | :--- |
| 보안 등급 분기 | 기밀 문서는 로컬, 일반 문서는 Claude |
| 작업 분기 | 대량 배치(데이터셋 생성)는 로컬, 최종 답변은 Claude |
| 폴백 | 로컬 우선, 실패·품질 미달 시 Claude |

**로컬 LLM 도입 시 주의**

- **모델 선택은 별도 평가가 필요합니다.** 한국어 LLM 순위는 임베딩보다 변동이 크고
  용도(요약/추출/추론)에 따라 결과가 달라지므로, 자사 문서로 직접 비교하십시오.
- **긴 근거를 다루려면 문맥 길이를 확인**해야 합니다. 표가 포함된 청크를 여러 개
  주입하면 컨텍스트가 빠르게 찹니다.
- **프롬프트 캐싱은 엔진마다 지원 여부가 다릅니다.** Claude 경로에서 쓰던
  `cache_control`이 그대로 적용되지 않으므로, 공급자 인터페이스가 이를 흡수해야 합니다.
- **JSON 구조화 출력 신뢰도가 낮을 수 있습니다.** 출처 표기처럼 형식이 중요한 응답은
  스키마 검증과 재시도를 공급자 바깥에 두십시오.

### 5.5 신설 엔드포인트

| 경로 | MCP 도구 | 동작 |
| :--- | :--- | :--- |
| `POST /api/search` | `search_knowledge` | 검색만 (현행 유지) |
| `POST /api/ask` | `ask_knowledge` | **검색 ➔ 근거 주입 ➔ 답변 생성 + 출처** |

응답 형태:

```json
{
  "answer": "1팀당 70만원이며 별도의 정산은 없습니다.",
  "sources": [
    {
      "doc_id": "hwp_a91c...",
      "source_file": "AI 커뮤니티 활동지원 모집공고.hwp",
      "block_id": "tbl1_r4",
      "quote": "커뮤니티 활동지원금 1팀당 70만원"
    }
  ],
  "confidence": 0.86
}
```

`quote`가 실제 청크에 존재하는지 검증하는 단계를 두면 환각을 차단할 수 있습니다.

---

## 6. 지식 저장소 접근 규칙

### 6.1 직접 접근 금지

```
[금지]  서비스 · 빌더 · API  ──직접──> ChromaDB

[권장]  서비스 · 빌더 · API  ──> KnowledgeStore 인터페이스 ──> JSON | SQLite | 기타
                                  put / get / list / delete
                                  is_stale / iter_blocks
```

여기저기서 ChromaDB를 직접 참조하면 저장소를 교체할 때 전면 재작성이 됩니다.
**인터페이스 하나만 통과하도록** 강제하십시오.

### 6.2 재생성은 "삭제 후 삽입"

현재 인덱싱 ID가 이렇게 생성됩니다.

```python
chunk_id = f"{source_file}_chunk_{idx}"   # upsert
```

20청크 문서를 12청크로 개정하면 **13~20번 옛 청크가 그대로 남습니다.**
`upsert`는 덮어쓸 뿐 초과분을 지우지 않습니다.

인덱스든 데이터셋이든 **기존 삭제 ➔ 신규 삽입**을 원칙으로 강제하십시오.

---

## 7. 선택 요약

| 계층 | 선택 | 현재 상태 |
| :--- | :--- | :--- |
| 임베딩 | **`snowflake-arctic-embed-l-v2.0-ko`** (1024차원, Apache-2.0) — Claude API엔 임베딩 없음 | 설정만 있고 미사용 |
| 지식 원천 | JSON/JSONL ➔ SQLite | **없음** |
| 벡터 인덱스 | ChromaDB | 있음 |
| 키워드 인덱스 | BM25 (전체 코퍼스·영속화) | 있으나 종속·비영속 |
| 타 시스템 | REST | 있음 (인증 없음) |
| 에이전트 도구 | MCP | 있음 |
| 에이전트 위임 | A2A | **없음** |
| 학습 | JSONL 내보내기 + 선택 의존성 | **없음** |
| 추론 LLM | `claude-opus-5` + adaptive thinking / **로컬 LLM(OpenAI 호환) 병용** | **없음** |
| 지식 접근 | `KnowledgeStore` 인터페이스 | **없음** |

---

## 8. 도입 순서

```
[0] 잔여 청크 버그 수정                    ← 지금도 잘못된 검색 결과를 만들고 있음
     ▼
[1] KnowledgeStore 인터페이스              ← 이후 모든 선택의 전제
     ├────────────────┬────────────────┐
     ▼                ▼                ▼
[2] 임베딩 교체     [3] 데이터셋      [4] 추론 계층
    (bge-m3)           (JSONL)          (claude-opus-5)
    + BM25 독립축                          │
     │                                     ▼
     └──────────────────────────────> [5] A2A / 레지스트리
```

**[1]을 선행시키는 이유**: 이것이 없으면 임베딩 교체는 재인덱싱 비용 때문에
비현실적이고, 데이터셋 빌더는 벡터DB를 역으로 긁게 되며, 추론 계층은 출처를
추적할 수 없습니다.

---

## 관련 문서

- [01. 지식 적재 ➔ 학습 ➔ 추론 ➔ API 제공 통합 구현 명세](./01_knowledge_training_inference_api_spec.md) — 아키텍처·스키마·단계별 구현
- [현행 시스템 실측 감사](../advancement/01_current_state_audit.md) — 본 문서 실측값의 상세 근거
- [임베딩·검색 공급자 추상화 설계](../advancement/03_embedding_provider_abstraction.md)
- [ML/DL 학습 데이터 계층 설계](../advancement/04_ml_dl_dataset_and_training.md)
- [A2A 프로토콜 및 허브 레지스트리 설계](../advancement/05_a2a_protocol_and_hub_registry.md)
