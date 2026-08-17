# 04. ML/DL 학습·추론 데이터 계층

> **선행 의존성**: [02_knowledge_store_abstraction.md](./02_knowledge_store_abstraction.md),
> [03_embedding_provider_abstraction.md](./03_embedding_provider_abstraction.md)

## 이 문서의 범위

본 문서는 학습 데이터 계층의 **스키마·인터페이스·작업 항목**을 정의합니다.
즉 *무엇을 만들 것인가*의 설계 계약입니다.

**무엇을 학습시키고 무엇을 학습시키지 않을 것인가**, 문서가 여러 개일 때의 처리,
LLM이 아닌 ML/DL 과제의 경로 같은 **판단 기준**은 별도 문서에 있습니다.

➔ **[지식을 학습 데이터로 만드는 방법](../rag_training_inference/04_knowledge_to_training_data.md)**

| 문서 | 다루는 것 |
| :--- | :--- |
| 본 문서 | `DatasetSample` 스키마, `DatasetBuilder`/`TrainingRunner` 인터페이스, 구현 작업 목록 |
| 위 문서 | 3계층 지식 분류, 근거 포함 학습, 다중 문서 충돌·편중·중복, ML/DL 경로 |

---

## 1. 현재 상태 (As-Is)

**학습 계층은 전혀 존재하지 않습니다.**

`src/core/config.py`에 `DATASETS_DIR`이 선언되어 있고 디렉토리까지 자동 생성되지만,

```python
DATASETS_DIR: Path = DATA_DIR / "datasets"
...
for d in [..., settings.DATASETS_DIR, ...]:
    d.mkdir(parents=True, exist_ok=True)
```

**여기에 쓰는 코드가 하나도 없습니다.** 빈 디렉토리만 만들어집니다.

`docs/03_agentic_rag_and_training.md`에 합성 QA 생성(Self-Instruct)과 LoRA 파이프라인
구상이 상세히 기술되어 있으나, 이는 설계 문서일 뿐 구현체가 없습니다.

### 왜 지금 당장 만들 수 없는가

현재 지식은 ChromaDB에 **800자로 잘린 청크**로만 존재합니다. 이 상태에서 학습
데이터를 만들면 다음 문제가 발생합니다.

- 문맥이 잘린 조각으로부터 QA를 생성 ➔ 저품질·환각 데이터
- 표가 중간에서 잘려 헤더 없는 행만 존재 ➔ 의미 없는 학습 샘플
- 원본 문서 단위로 묶을 수 없어 데이터 분할(train/valid) 시 **누수(leakage)** 발생
- 어떤 문서에서 나온 샘플인지 추적 불가 ➔ 품질 문제 발생 시 원인 파악 불가

**따라서 02번(KnowledgeStore)이 반드시 선행되어야 합니다.**

---

## 2. 목표 상태 (To-Be)

```
KnowledgeStore (02번)
        │
        │  record.blocks (타입 있는 구조화 블록)
        ▼
┌───────────────────────────────────────────────┐
│              DatasetBuilder                    │
│  ┌─────────────┬─────────────┬──────────────┐ │
│  │ SFT Builder │ QA Builder  │ Embedding    │ │
│  │ (지시학습)   │ (합성 QA)   │ Pair Builder │ │
│  └─────────────┴─────────────┴──────────────┘ │
└───────────────────┬───────────────────────────┘
                    │  data/datasets/{name}/{split}.jsonl
                    ▼
┌───────────────────────────────────────────────┐
│           TrainingRunner (어댑터)               │
│  LoRA/QLoRA │ 임베딩 파인튜닝 │ 분류기          │
└───────────────────┬───────────────────────────┘
                    │  학습된 모델
                    ▼
        03번 EmbeddingProvider / LLM 추론에 재투입
```

핵심은 **학습 프레임워크를 직접 품지 않는 것**입니다.
`DatasetBuilder`는 표준 포맷(JSONL)을 내보내고, 실제 학습은 어댑터가 위임합니다.
그래야 학습 환경(GPU 서버, Colab, 외부 플랫폼)을 자유롭게 선택할 수 있습니다.

---

## 3. 데이터셋 스키마

### 3.1 공통 래퍼

모든 샘플은 출처 추적 필드를 포함합니다.

```python
@dataclass
class DatasetSample:
    sample_id: str
    task_type: str              # sft | qa | embedding_pair | classification
    payload: dict               # 태스크별 내용 (3.2~3.4)

    # 출처 추적 (필수)
    doc_id: str
    block_ids: list[str]
    generated_by: str           # rule | llm:claude-opus-5 | human
    generated_at: datetime
    quality_score: float | None
    reviewed: bool = False
```

`doc_id`와 `block_ids`는 **선별 삭제·증분 갱신·분할 누수 방지**의 전제입니다.
상세한 근거와 다중 문서 상황에서의 활용은
[학습 데이터 만드는 방법 2.2 / 4.5](../rag_training_inference/04_knowledge_to_training_data.md)를 참조하십시오.

`block_ids`가 리스트인 이유는 **여러 문서에 걸친 샘플**과 **중복 제거 시 대표 샘플에
복수 출처를 기록**하기 위함입니다.

### 3.1.1 역인덱스

```
data/datasets/{name}/index/by_doc.json     # doc_id ➔ [sample_id, ...]
```

"문서 하나를 지우면 그 문서의 샘플만 제거"를 성립시키는 실체입니다.
이 파일이 없으면 선별 삭제가 불가능합니다.

### 3.2 SFT (지시 학습)

```json
{
  "messages": [
    {"role": "system", "content": "당신은 사내 지침을 준수하는 전문 AI 비서입니다."},
    {"role": "user", "content": "AI 커뮤니티 활동지원의 심사 배점 기준을 알려줘."},
    {"role": "assistant", "content": "심사기준은 100점 만점으로 다음과 같이 배분됩니다:\n- 주제성/타당성 20점\n- 커뮤니티 역량 30점\n- 활동계획 40점\n- 성남시민 참여비율 10점"}
  ]
}
```

### 3.3 임베딩 파인튜닝 쌍

```json
{
  "query": "커뮤니티 활동지원금은 얼마인가요?",
  "positive": "지원내용 | 커뮤니티 활동지원금 1팀당 70만원, AI 전문가 멘토링 지원(2회) ...",
  "negatives": ["제출서류 | ① AI 커뮤니티 활동지원 신청서 ...", "..."]
}
```

Hard negative는 **같은 문서의 다른 블록**에서 뽑는 것이 효과적입니다.
무관한 문서에서 뽑으면 너무 쉬운 음성 샘플이 되어 학습 효과가 떨어집니다.
02번의 `iter_blocks()`가 이를 값싸게 만들어 줍니다.

### 3.4 저장 레이아웃

```
data/datasets/
└── {dataset_name}/
    ├── manifest.json      # 생성 조건, 소스 doc_id 목록, 통계, 빌더 버전
    ├── train.jsonl
    ├── valid.jsonl
    └── rejected.jsonl     # 품질 필터 탈락 샘플 (원인 분석용)
```

`manifest.json`에 생성 조건을 남겨야 **동일 데이터셋을 재현**할 수 있습니다.
`rejected.jsonl`을 남기는 이유는 필터가 너무 공격적이어서 좋은 샘플을 버리고 있지는
않은지 검토하기 위함입니다.

---

## 4. DatasetBuilder 인터페이스

```python
class DatasetBuilder(Protocol):
    task_type: str

    def build(
        self,
        store: KnowledgeStore,
        filters: DatasetFilter,      # category / file_type / tags / 기간
        options: dict,
    ) -> DatasetBuildResult: ...
```

```python
@dataclass
class DatasetFilter:
    categories: list[str] | None = None
    file_types: list[str] | None = None
    tags: list[str] | None = None
    doc_ids: list[str] | None = None
    min_block_count: int = 1
```

`KnowledgeStore.list()`(02번 4절)를 그대로 사용하므로 별도 조회 로직이 필요 없습니다.

### 4.1 빌더 구현체

| 빌더 | 생성 방식 | 비용 |
| :--- | :--- | :--- |
| `TableQABuilder` | 규칙 — `TableData`의 헤더 행과 데이터 행 매핑 | 0원, 환각 없음 |
| `SFTBuilder` | LLM — 블록 문맥을 주고 질문·답변 생성 | 호출당 과금, 검수 필요 |
| `EmbeddingPairBuilder` | 규칙 + LLM — 질의 생성 및 hard negative 선별 | 혼합 |

LLM 공급자는 03번의 공급자 추상화와 동일한 방식으로 인터페이스 뒤에 두어
교체 가능하게 합니다.

> 각 빌더가 **무엇을 샘플로 만들어야 하는가**(사실이 아니라 적용 능력, 근거를
> 포함한 형태)는
> [학습 데이터 만드는 방법 3절](../rag_training_inference/04_knowledge_to_training_data.md)에 있습니다.

### 4.2 빌드 옵션

```python
@dataclass
class BuildOptions:
    max_samples_per_doc: int = 50        # 문서당 상한 (편중 방지)
    min_samples_per_doc: int = 1
    balance_by: str | None = "category"  # 층화 기준
    dedup_threshold: float = 0.95        # 근접 중복 판정 임계값
```

### 4.3 품질 필터

| 필터 | 목적 |
| :--- | :--- |
| 근거 포함 검증 | 답변의 핵심 문자열이 원본 블록에 실제로 존재하는가 |
| 중복 제거 | 정규화 일치 ➔ 질문 임베딩 유사도 |
| 길이/형식 검증 | 비정상적으로 짧거나 잘린 샘플 제거 |
| 공란 셀 배제 | 빈 서식의 공란에서 무의미한 QA가 생성되는 것 방지 |
| **모순 탐지** | 질문은 유사한데 답이 다른 쌍을 검수 대상으로 보고 |

마지막 항목은 문서가 여러 개일 때만 나타납니다. 필터가 아니라 **보고**입니다 —
자동 폐기하지 않고 사람이 판단하게 넘깁니다.

---

## 5. TrainingRunner (어댑터)

```python
class TrainingRunner(Protocol):
    def train(self, dataset_dir: Path, config: TrainingConfig) -> TrainingResult: ...
```

| 어댑터 | 대상 | 출력 |
| :--- | :--- | :--- |
| `ExportOnlyRunner` | 외부 플랫폼 학습용 | JSONL만 내보내고 종료 (**기본값**) |
| `EmbeddingRunner` | 임베딩 파인튜닝 (sentence-transformers) | 임베딩 모델 |
| `RerankerRunner` | Cross-Encoder 리랭커 | 리랭커 모델 |
| `ClassifierRunner` | 분류·회귀 (카테고리, 양식 판별 등) | 분류기 |
| `LoRARunner` | LLM 지시 학습 (peft/trl) | LoRA 어댑터 |

> **LLM이 아닌 ML/DL 과제**(리랭커·분류기)는 학습 데이터 형태가 `(특징 X, 레이블 y)`로
> 근본적으로 다르고, **추론 시 LLM을 두지 않습니다.** 어떤 과제가 우선순위가 높은지,
> 지식베이스에서 X와 y를 어떻게 뽑는지는
> [학습 데이터 만드는 방법 7절](../rag_training_inference/04_knowledge_to_training_data.md)을 참조하십시오.

**`ExportOnlyRunner`를 기본값으로 둡니다.** 학습 프레임워크(torch, peft, trl)는
무겁고 GPU 환경에 종속적이므로, 본 프로젝트의 핵심 의존성에 넣지 않습니다.
`optional-dependencies`로 분리하여 필요한 사람만 설치하게 합니다.

```toml
[project.optional-dependencies]
training = ["torch", "transformers", "peft", "trl", "sentence-transformers"]
```

### 5.1 학습 결과의 추론 재투입

```
EmbeddingRunner ──> models/finetuned/{run_id}/
                            │
                            ▼
              settings.FINETUNED_MODEL_PATH 지정
                            │
                            ▼
              03번 FineTunedEmbedding 공급자가 로드
                            │
                            ▼
              재인덱싱 (02번 KnowledgeStore에서 값싸게 수행)
```

이 순환이 성립하려면 02번과 03번이 모두 필요합니다.
**02번이 없으면 재인덱싱 비용이 너무 커서 모델 교체가 현실적이지 않고,
03번이 없으면 학습한 모델을 꽂을 자리가 없습니다.**

---

## 6. 노출 도구

| 도구 | 용도 |
| :--- | :--- |
| `build_dataset(name, task_type, filters)` | 데이터셋 생성 |
| `list_datasets()` | 생성된 데이터셋 목록 및 통계 |
| `get_dataset_manifest(name)` | 생성 조건·소스 문서 확인 |
| `export_dataset(name, format)` | JSONL / HuggingFace 포맷 내보내기 |

MCP와 REST 양쪽에 동일하게 노출하여, 외부 에이전트가 "지식 베이스에서 학습 데이터를
만들어 달라"고 요청할 수 있게 합니다.

---

## 7. 작업 항목

| # | 작업 | 산출물 | 선행 |
| :--- | :--- | :--- | :--- |
| 1 | 데이터셋 스키마 정의 | `src/training/schema.py` | 02 |
| 2 | 규칙 기반 표➔QA 빌더 | `src/training/builders/table_qa.py` | 1 |
| 3 | 품질 필터 | `src/training/filters.py` | 1 |
| 4 | 문서 단위 train/valid 분할 | `src/training/split.py` | 1 |
| 5 | SFT 빌더 (LLM) | `src/training/builders/sft.py` | 2, 3 |
| 6 | 임베딩 쌍 빌더 | `src/training/builders/embedding_pair.py` | 2, 3 |
| 7 | `ExportOnlyRunner` | `src/training/runners/export.py` | 4 |
| 8 | MCP/REST 도구 추가 | `src/mcp_server.py`, `src/api/server.py` | 7 |
| 9 | `EmbeddingRunner` (선택 의존성) | `src/training/runners/embedding.py` | 6, 03 |
| 10 | `LoRARunner` (선택 의존성) | `src/training/runners/lora.py` | 5 |

**2번(규칙 기반)을 5번(LLM 기반)보다 먼저 하는 이유**: LLM 호출 없이 즉시 검증
가능하고, 비용이 들지 않으며, 환각이 없어 파이프라인 전체의 정합성을 먼저 확인할 수
있습니다. 표 기반 QA만으로도 실용적인 데이터셋이 나옵니다.

---

## 8. 완료 판정 기준 (인터페이스 관점)

본 문서가 정의한 **계약이 성립하는가**를 봅니다.

- [ ] `DatasetSample`이 출처 필드(`doc_id`/`block_ids`/`parser_version`)를 모두 담는다
- [ ] `by_doc.json` 역인덱스로 **문서별 샘플 선별 삭제**가 동작한다
- [ ] `DatasetBuilder`가 `KnowledgeStore.list()`만으로 소스를 조회한다 (벡터DB 직접 접근 없음)
- [ ] `BuildOptions`의 문서당 상한·층화가 실제로 적용된다
- [ ] `manifest.json`으로 데이터셋 생성 조건이 재현된다
- [ ] `ExportOnlyRunner`가 기본값이며, 학습 프레임워크 미설치 상태에서도 동작한다
- [ ] 파인튜닝한 임베딩 모델을 설정 변경만으로 추론에 투입할 수 있다

> **데이터 품질 관점**의 판정 기준(모순 탐지, 보일러플레이트 중복, 공란 셀, 증분 갱신)은
> [학습 데이터 만드는 방법 10절](../rag_training_inference/04_knowledge_to_training_data.md)에 있습니다.
