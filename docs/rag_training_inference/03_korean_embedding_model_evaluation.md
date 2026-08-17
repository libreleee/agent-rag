# 한국어 임베딩 모델 조사 및 선정

한국어 RAG에 쓸 임베딩 모델을 **어떤 근거로 고를 것인가**를 정리한 문서입니다.
리더보드 조사 결과, 후보 비교, 권장안, 그리고 **자체 평가 방법**을 담습니다.

**조사 기준일: 2026년 8월 17일**

> 임베딩 모델 순위는 빠르게 바뀝니다. 이 문서는 조사 시점의 스냅샷이며,
> 도입 전에 반드시 [7절의 자체 평가](#7-자체-평가가-최종-근거입니다)를 수행하십시오.

---

## 1. 왜 다시 조사했는가

프로젝트 설정에는 `EMBEDDING_MODEL = "BAAI/bge-m3"`가 선언되어 있습니다.
`bge-m3`는 오랫동안 한국어 오픈소스 임베딩의 사실상 표준이었으나,
**2026년 8월 기준으로는 더 이상 1위가 아닙니다.**

또한 실측 결과 이 설정값은 **코드 어디에서도 참조되지 않으며**, 실제로는
ChromaDB 기본 임베딩(384차원, all-MiniLM 계열)이 동작하고 있었습니다.
어차피 임베딩 계층을 새로 만들어야 하므로, 이 시점에 모델을 재선정합니다.

관련 실측 근거: [현행 시스템 실측 감사 3.2](../advancement/01_current_state_audit.md)

---

## 2. 리더보드 조사 결과

한국어 MTEB 리더보드 기준이며, 지표는 **NDCG@5와 @10의 평균**입니다.
평가 데이터셋은 Ko-StrategyQA, AutoRAG Retrieval, PublicHealthQA, LawIRKo,
WebFAQRetrieval, SQuADKorV1Retrieval, MIRACL Retrieval(Hard Negative) 등입니다.

### 2.1 Dense 부문

| 순위 | 모델 | 점수 | 규모 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `perplexity-ai/pplx-embed-v1-4b` | 82.79 | 4B | 무거움. 라이선스 확인 필요 |
| 2 | **`dragonkue/snowflake-arctic-embed-l-v2.0-ko`** | **82.14** | **0.6B** | **Apache-2.0** |
| 3 | `telepix/PIXIE-Rune-v1.0` | 81.57 | — | |

### 2.2 Sparse 부문

| 순위 | 모델 | 점수 |
| :--- | :--- | :--- |
| 1 | `telepix/PIXIE-Splade-v1.5` | 78.19 |
| 2 | `yjoonjang/splade-ko-v1` | 77.00 |
| 3 | `yjoonjang/inference-free-splade-ko-v1` | 76.75 |

Sparse 부문이 따로 존재한다는 점이 중요합니다 — BM25를 학습 기반 모델로
대체할 수 있는 선택지가 생겼다는 뜻입니다. (5절 참조)

---

## 3. 권장: `dragonkue/snowflake-arctic-embed-l-v2.0-ko`

**1위가 아니라 2위를 권합니다.** 근거는 성능 대비 무게입니다.

| 항목 | 값 |
| :--- | :--- |
| 파라미터 | **0.6B** — 1위(4B) 대비 6배 이상 가벼움 |
| 임베딩 차원 | **1024** |
| 최대 입력 | **8192 토큰** |
| 라이선스 | **Apache-2.0** (상업적 이용·수정·배포 자유) |
| 기반 | Snowflake Arctic Embed L v2.0 한국어 파인튜닝 |

### 3.1 선정 이유

**① 점수 차이가 작고 무게 차이가 큽니다.**
1위와 0.65점 차이인데 모델 크기는 6배 이상 차이납니다. 온프레미스 서빙과
재인덱싱 비용을 고려하면 실용적으로 2위가 낫습니다.

**② 차원이 1024로 bge-m3와 같습니다.**
인덱스 차원 설계가 동일하므로, 나중에 bge-m3로 되돌리거나 비교 실험할 때
저장소 구조를 바꾸지 않아도 됩니다.

**③ 라이선스가 명확합니다.**
Apache-2.0은 기업 환경에서 가장 다루기 쉬운 조건입니다.

**④ 8192 토큰 문맥은 공문서에 유리합니다.**
성남시 공고문처럼 표가 많은 행정 문서는 청크가 길어지기 쉽습니다.

### 3.2 bge-m3 대비 실측 비교

모델 제작자가 공개한 한국어 검색 벤치마크 수치입니다.

| 벤치마크 | arctic-embed-ko | bge-m3 |
| :--- | :--- | :--- |
| **평균 NDCG@10** | **0.7404** | 0.7242 |
| XPQARetrieval | **0.4436** | 0.3608 |
| AutoRAGRetrieval | **0.9093** | 0.8301 |

제작자는 여러 도메인에서 일관되게 bge-m3를 앞섰다고 보고합니다.

> 제작자 자체 보고 수치이므로, 7절의 자체 평가로 교차 확인하십시오.

---

## 4. 후보 비교

| 모델 | 차원 | 라이선스 | 언제 선택하나 |
| :--- | :--- | :--- | :--- |
| **`snowflake-arctic-embed-l-v2.0-ko`** | 1024 | Apache-2.0 | **기본 권장.** 성능·무게·라이선스 균형 |
| `BAAI/bge-m3` | 1024 | MIT | Dense와 Sparse를 **한 모델로** 처리하고 싶을 때 |
| `nlpai-lab/KURE-v1` | 1024 | — | bge-m3 기반 한국어 특화 파인튜닝. 별도 리더보드 상위 |
| `perplexity-ai/pplx-embed-v1-4b` | — | 확인 필요 | 최고 점수가 필요하고 4B 서빙이 감당될 때 |
| ChromaDB 기본 | 384 | — | 현행 동작(변경 없음). **한국어 취약** |

---

## 5. Dense / Sparse 조합 결정

`arctic-embed-ko`는 **Dense 전용**입니다. `bge-m3`는 한 모델에서 Dense와
Sparse를 함께 냅니다. 이 차이가 아키텍처 선택으로 이어집니다.

| 안 | 구성 | 평가 |
| :--- | :--- | :--- |
| **A (권장)** | `arctic-embed-ko` + **BM25** | 두 축이 완전히 독립. 본 프로젝트 설계와 일치 |
| B | `bge-m3` 단독 | 모델 하나로 단순하나 Dense 성능이 A보다 낮음 |
| C | `arctic-embed-ko` + **한국어 SPLADE** | Sparse도 학습 모델로. 인덱싱 비용 큼 |

**A안으로 시작하십시오.**

BM25는 한국어에서 조사가 붙는 문제가 있습니다 — "지원금을"과 "지원금"이
다른 토큰이 되어 매칭률이 떨어집니다. 형태소 분석기(`kiwipiepy` 등)를
선택 의존성으로 붙이면 상당 부분 완화됩니다.

그래도 부족하면 **그때** C안(SPLADE)을 검토하십시오. 처음부터 SPLADE를
도입하면 인덱싱 파이프라인이 무거워지고, 실제로 필요한지 검증되지 않은 채
복잡도만 올라갑니다.

---

## 6. 도입 시 주의사항

### 6.1 차원 변경은 전량 재인덱싱을 강제합니다

```
현행 384차원 (ChromaDB 기본)  ──>  1024차원 (arctic-embed-ko)
                                    기존 인덱스와 호환 불가
```

컬렉션 메타데이터에 공급자와 차원을 기록해, 불일치를 **조용한 오작동이 아니라
명시적 오류**로 잡아야 합니다.

```python
collection = client.get_or_create_collection(
    name="enterprise_knowledge",
    metadata={"embedding_provider": provider.name, "dimension": provider.dimension},
)
```

> KnowledgeStore가 선행되어야 재인덱싱이 값싼 작업이 됩니다.
> 원본 파일부터 다시 파싱해야 한다면 모델 교체는 현실적인 선택지가 아닙니다.

### 6.2 질의와 문서의 프리픽스가 다를 수 있습니다

다수의 임베딩 모델이 질의에 별도 프리픽스(`"query: "` 등)를 요구합니다.
이를 호출부가 아니라 **공급자 내부에서 처리**해야 모델 교체 시 호출부가
영향받지 않습니다.

```python
class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...   # 프리픽스는 여기서
```

### 6.3 의존성이 추가됩니다

현재 `sentence-transformers`와 `torch`가 **모두 미설치**입니다.
로컬 임베딩 모델을 쓰려면 설치가 필요하며, 용량이 큽니다.

핵심 의존성에 넣을지 선택 의존성으로 뺄지 결정하십시오.
기본값을 ChromaDB 내장 임베딩으로 두면 미설치 상태에서도 동작합니다.

---

## 7. 자체 평가가 최종 근거입니다

### 7.1 리더보드 점수를 교차 비교하지 마십시오

조사 중 `KURE-v1`이 83.37점(5위)이라는 수치도 확인됐습니다.
이는 **다른 리더보드**의 값이라, 2절 표의 82.14보다 높다고 해석하면 안 됩니다.
평가 데이터셋과 지표가 다르기 때문입니다.

> 같은 리더보드 안에서의 상대 순위만 의미가 있습니다.

### 7.2 자사 문서로 평가하십시오

행정 문서는 일반 벤치마크와 성격이 다릅니다 — 표가 많고, 고유명사와 금액·
날짜가 핵심이며, 빈 양식지가 섞여 있습니다.

**평가셋 만들기**

1. 실제 문서에서 질문–정답 청크 쌍을 30~50개 만듭니다.
   (표 기반 규칙 생성으로 상당수를 자동 생성할 수 있습니다)
2. 반드시 다음 유형을 섞습니다.

| 유형 | 예시 | 무엇을 보나 |
| :--- | :--- | :--- |
| 고유 문자열 | "공고 제96호" | Sparse 축이 동작하는가 |
| 금액·수치 | "지원금은 얼마인가" | 표 청크를 회수하는가 |
| 표 내부 값 | "주제성/타당성 배점은" | 헤더-값 연결이 유지되는가 |
| 서술형 | "필수 이행사항은" | Dense 축이 의미를 잡는가 |

**측정 지표**

| 지표 | 의미 |
| :--- | :--- |
| Recall@10 | 정답 청크가 상위 10개 안에 있는가 (가장 중요) |
| NDCG@10 | 정답이 얼마나 위에 있는가 |
| MRR | 첫 정답의 순위 |

**비교 대상**

```
[기준선] ChromaDB 기본 (384차원)          ← 현행
[후보 1] arctic-embed-ko (1024차원)
[후보 2] bge-m3 (1024차원)
[후보 3] 후보 1 + BM25 하이브리드
```

기준선을 반드시 포함하십시오. **"바꿔서 얼마나 좋아졌는가"** 를 수치로
말할 수 없으면 교체를 정당화할 수 없습니다.

### 7.3 평가 자동화

이 평가셋은 임베딩 선정에만 쓰이는 것이 아닙니다.
[검색 품질 회귀 테스트](../advancement/03_embedding_provider_abstraction.md)의
기반이 되므로, 일회성 스크립트가 아니라 **저장소에 두고 반복 실행**하십시오.

---

## 8. 결론

| 항목 | 결정 |
| :--- | :--- |
| Dense 임베딩 | **`dragonkue/snowflake-arctic-embed-l-v2.0-ko`** (1024차원, Apache-2.0) |
| Sparse | **BM25** + 한국어 형태소 분석기 (선택 의존성) |
| 폴백 기본값 | ChromaDB 내장 임베딩 (의존성 미설치 시에도 동작) |
| 확정 조건 | **7절 자체 평가에서 기준선 대비 개선이 확인될 것** |

임베딩 교체는 KnowledgeStore 구축 이후에 진행하십시오.
그 전에는 재인덱싱 비용 때문에 실행이 어렵습니다.

---

## 참고 자료

- [ko-embedding-leaderboard (Korean-MTEB)](https://github.com/OnAnd0n/ko-embedding-leaderboard) — 2절 순위의 출처
- [dragonkue/snowflake-arctic-embed-l-v2.0-ko](https://huggingface.co/dragonkue/snowflake-arctic-embed-l-v2.0-ko) — 3절 사양 및 bge-m3 비교 수치
- [KURE — 한국어 특화 임베딩 모델](https://yjoonjang.medium.com/koe5-%EC%B5%9C%EC%B4%88%EC%9D%98-%ED%95%9C%EA%B5%AD%EC%96%B4-%EC%9E%84%EB%B2%A0%EB%94%A9-%EB%AA%A8%EB%8D%B8-multilingual-e5-finetune-22fa7e56d220)
- [The Best Open-Source Embedding Models in 2026 — BentoML](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- [BAAI/bge-m3 vs Qwen3 Embedding 비교](https://agentset.ai/embeddings/compare/baaibge-m3-vs-qwen3-embedding-06b)

## 관련 문서

- [02. 기술 선택 및 인터페이스 명세](./02_technology_stack_and_interfaces.md) — 본 문서의 결론이 반영된 곳
- [01. 지식 적재 ➔ 학습 ➔ 추론 ➔ API 제공 통합 구현 명세](./01_knowledge_training_inference_api_spec.md)
- [임베딩·검색 공급자 추상화 설계](../advancement/03_embedding_provider_abstraction.md)
