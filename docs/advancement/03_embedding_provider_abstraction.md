# 03. 임베딩 및 검색 공급자 추상화

> **선행 의존성**: [02_knowledge_store_abstraction.md](./02_knowledge_store_abstraction.md)
> **후행 작업**: 04(학습 계층) — 학습한 모델을 추론에 재투입하려면 본 계층이 필요

---

## 1. 현재 상태 (As-Is)

### 1.1 설정된 임베딩 모델이 무시되고 있음

`src/core/config.py`:

```python
EMBEDDING_MODEL: str = "BAAI/bge-m3"
```

`src/rag/indexer.py`:

```python
self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
# 임베딩 함수를 지정하지 않음 ➔ ChromaDB 기본 내장 임베딩 사용
```

`EMBEDDING_MODEL` 설정값은 **코드 어디에서도 참조되지 않습니다.** 죽은 설정입니다.

ChromaDB 기본 임베딩은 `all-MiniLM-L6-v2` 계열로, 한국어 성능이 `bge-m3`에 비해
현저히 떨어집니다. 즉 **설정 파일을 읽은 사람이 기대하는 성능과 실제 성능이 다릅니다.**

### 1.2 하이브리드 검색의 구조적 한계

`src/rag/retriever.py`에 BM25는 **실제로 구현되어 있습니다.** 다만 세 가지 한계가 있습니다.

**한계 ①: BM25가 독립 검색 축이 아님 (가장 중요)**

```python
results = self.collection.query(query_texts=[query], n_results=min(top_k * 2, 20))
documents = results.get("documents", [[]])[0]
...
tokenized_corpus = [doc.split() for doc in documents]   # ← 벡터 결과에만 BM25 적용
bm25 = BM25Okapi(tokenized_corpus)
```

BM25 코퍼스가 **벡터 검색이 반환한 최대 20개 문서**로 한정됩니다.
벡터 검색이 놓친 문서는 BM25로도 결코 복구되지 않습니다.

하이브리드 검색의 존재 이유는 "품번 `SM-2026-A`", "공고 제96호" 같은 고유 문자열을
벡터가 못 잡을 때 키워드가 잡아주는 것입니다. 현 구조는 그 목적을 달성하지 못하고
**벡터 결과의 재정렬**에 머뭅니다.

**한계 ②: RRF가 아닌 가중 선형 결합**

주석은 "RRF 방식"이라 명시하지만 실제 코드는 가중 합산입니다.

```python
final_score = (vector_score * 0.6) + (min(bm25_score / 10.0, 1.0) * 0.4)
```

BM25 점수를 `/10.0`으로 나누는 정규화는 코퍼스 크기와 질의 길이에 따라 척도가 달라져
안정적이지 않습니다. RRF는 점수가 아닌 **순위**를 융합하므로 이 문제가 없습니다.

**한계 ③: 매 질의마다 인덱스 재구축 + 한국어 토크나이징 부재**

- `BM25Okapi(...)`가 `search()` 호출마다 새로 생성됩니다.
- `doc.split()`은 공백 분리이므로 "지원금을"과 "지원금"이 다른 토큰이 됩니다.
  한국어는 조사가 붙으므로 형태소 분석 없이는 키워드 매칭률이 크게 떨어집니다.

### 1.3 모델 교체 지점이 없음

임베딩 생성이 ChromaDB 내부에 묻혀 있어, 다른 모델로 교체하거나
**파인튜닝한 자체 모델을 투입할 지점이 존재하지 않습니다.**
04번 문서의 학습 결과물을 추론에 되먹이려면 이 지점이 반드시 필요합니다.

---

## 2. 목표 상태 (To-Be)

```
                  ┌──────────────────────┐
                  │  EmbeddingProvider   │  ← 인터페이스
                  └──────────┬───────────┘
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ChromaDefault        BGE-M3(로컬)        FineTuned(자체 학습)
  (의존성 없음)         SentenceTransformer   04번 산출물
```

```
                  ┌──────────────────────┐
                  │      Retriever       │
                  └──────────┬───────────┘
              ┌──────────────┴──────────────┐
              ▼                             ▼
      DenseRetriever                 SparseRetriever
      (Vector / Chroma)              (BM25, 전체 코퍼스)
              └──────────────┬──────────────┘
                             ▼
                    RRF Fusion (순위 융합)
                             ▼
                    Reranker (선택, Cross-Encoder)
```

---

## 3. 인터페이스 정의

### 3.1 EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    name: str
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
```

`embed_documents`와 `embed_query`를 분리하는 이유는 bge-m3 등 다수 모델이
질의에 별도 프리픽스(`"query: "`)를 요구하기 때문입니다. 이를 호출부가 아니라
공급자 내부에서 처리해야 모델 교체 시 호출부가 영향받지 않습니다.

**구현체:**

| 구현체 | 용도 | 비고 |
| :--- | :--- | :--- |
| `ChromaDefaultEmbedding` | 현행 동작 유지 | 하위 호환, 기본값 |
| `SentenceTransformerEmbedding` | `bge-m3` 등 로컬 모델 | `EMBEDDING_MODEL` 설정을 **실제로** 사용 |
| `FineTunedEmbedding` | 04번에서 학습한 모델 | 학습➔추론 순환 완성 |

### 3.2 차원 불일치 방어

임베딩 모델을 바꾸면 벡터 차원이 달라져 기존 컬렉션과 호환되지 않습니다.
이를 런타임에 감지해야 합니다.

```python
# 컬렉션 메타데이터에 공급자 정보 기록
collection = client.get_or_create_collection(
    name="enterprise_knowledge",
    metadata={"embedding_provider": provider.name, "dimension": provider.dimension},
)
# 불일치 시 명시적 오류 + 재인덱싱 안내
```

이것이 없으면 모델 교체 후 검색 결과가 조용히 망가집니다.
**02번의 KnowledgeStore가 있으면 재인덱싱이 값싼 작업이 되므로** 모델 교체가
현실적인 선택지가 됩니다. 이것이 02번을 선행으로 두는 이유 중 하나입니다.

### 3.3 Retriever 재구성

```python
class SparseRetriever(Protocol):
    def build(self, store: KnowledgeStore) -> None:
        """KnowledgeStore 전체를 코퍼스로 BM25 인덱스 구축 후 디스크 영속화."""

    def search(self, query: str, top_k: int) -> list[ScoredChunk]: ...
```

```python
class HybridRetriever:
    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        dense = self.dense.search(query, top_k=self.candidate_k)    # 독립 실행
        sparse = self.sparse.search(query, top_k=self.candidate_k)  # 독립 실행
        fused = reciprocal_rank_fusion([dense, sparse], k=60)
        if self.reranker:
            fused = self.reranker.rerank(query, fused, top_k=top_k)
        return fused[:top_k]
```

**핵심 변경**: `dense`와 `sparse`가 각각 **전체 코퍼스를 독립적으로 검색**합니다.
현재처럼 sparse가 dense 결과에 종속되지 않습니다.

### 3.4 RRF 구현

```python
def reciprocal_rank_fusion(rank_lists, k: int = 60) -> list[SearchResult]:
    scores = defaultdict(float)
    for ranked in rank_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item.chunk_id] += 1.0 / (k + rank)
    return sorted(...)
```

점수가 아닌 **순위**만 사용하므로 BM25와 코사인 유사도의 척도 차이를 정규화할 필요가
없습니다. 1.2절 한계 ②의 `/10.0` 임의 정규화 문제가 사라집니다.

### 3.5 한국어 토크나이저

```python
class Tokenizer(Protocol):
    def tokenize(self, text: str) -> list[str]: ...
```

| 구현체 | 비고 |
| :--- | :--- |
| `WhitespaceTokenizer` | 현행 동작 (`doc.split()`), 기본값 |
| `KiwiTokenizer` | `kiwipiepy` 형태소 분석. 조사 분리로 매칭률 개선 |

형태소 분석기는 선택 의존성으로 두어, 미설치 시 공백 분리로 자동 폴백합니다.
새 의존성을 강제하지 않으면서 개선 경로를 열어두기 위함입니다.

---

## 4. 설정 확장

```python
class Settings(BaseSettings):
    # 임베딩
    EMBEDDING_PROVIDER: str = "chroma_default"   # chroma_default | sentence_transformer | finetuned
    EMBEDDING_MODEL: str = "BAAI/bge-m3"         # 이제 실제로 사용됨
    EMBEDDING_DEVICE: str = "cpu"                # cpu | cuda
    FINETUNED_MODEL_PATH: Path | None = None     # 04번 산출물 경로

    # 검색
    RETRIEVAL_CANDIDATE_K: int = 30              # 융합 전 각 축의 후보 수
    RRF_K: int = 60
    SPARSE_TOKENIZER: str = "whitespace"         # whitespace | kiwi
    ENABLE_RERANKER: bool = False
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
```

기본값을 **현행 동작과 동일하게** 두어, 설정을 바꾸지 않으면 기존과 같이 동작합니다.
이렇게 해야 점진적 이행이 가능합니다.

---

## 5. 작업 항목

| # | 작업 | 산출물 | 선행 |
| :--- | :--- | :--- | :--- |
| 1 | `EmbeddingProvider` 인터페이스 + 기본 구현 | `src/embeddings/base.py`, `chroma_default.py` | - |
| 2 | `SentenceTransformerEmbedding` 구현 | `src/embeddings/sentence_transformer.py` | 1 |
| 3 | 인덱서/검색기에 공급자 주입 | `src/rag/indexer.py`, `retriever.py` | 1 |
| 4 | 차원 불일치 감지 | `src/rag/indexer.py` | 3 |
| 5 | BM25 독립 인덱스 (전체 코퍼스, 영속화) | `src/rag/sparse.py` | 02번 완료 |
| 6 | RRF 융합으로 교체 | `src/rag/fusion.py` | 5 |
| 7 | 한국어 토크나이저 (선택 의존성) | `src/rag/tokenizer.py` | 5 |
| 8 | Reranker (선택) | `src/rag/reranker.py` | 6 |
| 9 | 검색 품질 회귀 테스트 | `tests/test_retrieval.py` | 6 |

**5번이 02번 완료에 의존하는 이유**: BM25 전체 코퍼스 인덱스를 만들려면
전체 청크를 열거할 수 있어야 하는데, 현재는 ChromaDB에서 전량을 긁는 방법밖에 없습니다.
KnowledgeStore가 있으면 거기서 직접 구축할 수 있습니다.

---

## 6. 검증 방법

9번 회귀 테스트에는 최소한 다음 케이스를 포함합니다.

| 케이스 | 확인 내용 |
| :--- | :--- |
| 고유 문자열 질의 ("공고 제96호") | BM25 축이 독립 동작하여 정확히 회수되는가 |
| 개념 질의 ("지원금은 얼마인가") | 벡터 축이 표 청크를 회수하는가 |
| 표 내부 값 질의 ("심사 배점") | 02번의 표 통짜 청킹 덕분에 헤더와 값이 함께 반환되는가 |
| 모델 교체 후 | 차원 불일치가 조용한 실패 없이 명시적 오류로 감지되는가 |

세 번째 케이스는 02번과 03번이 함께 동작해야 통과합니다.
01번에서 복원한 심사 배점표(100점 만점 배분)가 좋은 테스트 소재입니다.

---

## 7. 완료 판정 기준

- [ ] `EMBEDDING_MODEL` 설정이 실제 임베딩 생성에 반영된다
- [ ] 벡터 검색이 놓친 문서를 BM25 축이 독립적으로 회수한다
- [ ] 점수 융합이 임의 정규화 없는 RRF로 동작한다
- [ ] BM25 인덱스가 질의마다 재구축되지 않는다
- [ ] 임베딩 모델 교체 시 차원 불일치가 명시적 오류로 감지된다
- [ ] 04번에서 학습한 모델을 설정 변경만으로 투입할 수 있다
