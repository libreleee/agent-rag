# 03. 추론(RAG) 및 모델 학습(Training) 파이프라인

본 장에서는 구조화된 KM 데이터를 바탕으로 **실시간 추론(Inference / Agentic RAG)**과 **도메인 특화 모델 학습(Training / Fine-Tuning)**을 구축하는 기술적 세부사항을 다룹니다.

---

## 1. 실시간 추론 레이어: Agentic RAG 파이프라인

기존 단순 RAG(질문 ➔ 1회 검색 ➔ 답변)의 한계를 극복하기 위해, 에이전트가 추론 과정을 주도하는 **Agentic RAG** 워크플로우를 적용합니다.

```
[사용자 질의] 
      │
      ▼
[1. Query Analyzer & Rewriter] ──> 복합 질의 분해 및 키워드 최적화
      │
      ▼
[2. Hybrid Search (Dense + Sparse)]
 ├── Dense Vector: BGE-m3 / OpenAI Text-Embedding-3
 └── Sparse Keyword: BM25 / SPLADE
      │
      ▼
[3. Re-ranking (재순위화)] ──> Cohere Rerank / BGE-Reranker-Large (상위 3~5개 선별)
      │
      ▼
[4. LLM Grader (문서 연관성 자체 검증)]
 ├── 관련성 부족 시 ──> [Query Rewrite 후 재검색 (다단계 루프)]
 └── 관련성 충분 시 ──> [5. 최종 응답 생성 (Context 주입)]
      │
      ▼
[6. Hallucination Grader (환각 검증)] ──> 출처 기반 팩트 체크 후 사용자 반환
```

### 핵심 RAG 컴포넌트
1. **하이브리드 검색 (Hybrid Search)**: 
   - 전문 용어, 품번, 약어는 BM25(키워드)가 정확히 잡고,
   - 개념적/자연어 질의는 Dense Vector(의미 임베딩)가 잡아 상호 보완(RRF, Reciprocal Rank Fusion 적용).
2. **Re-ranker**:
   - 1차 검색된 청크(Top 20~50개) 중 질문과 문맥적 일치도가 가장 높은 상위 3~5개만 LLM에 전달하여 토큰 비용 절감 및 환각 방지.

---

## 2. 모델 학습(Training) 레이어: 도메인 파인튜닝

문서의 팩트 자체는 RAG로 실시간 제공하되, **사내 특유의 개조식 보고서 문체, 행정/전문 용어 해석 능력, 지시사항 준수율**을 극대화하기 위해 Fine-Tuning(SFT/LoRA)을 수행합니다.

### ① KM 기반 합성 QA 데이터셋 생성 파이프라인 (Self-Instruct)
사내 문서를 입력받아 고품질 `(Instruction, Context, Response)` 트리플릿을 자동 생성합니다.

```
[파싱된 KM 문서 청크]
        │
        ▼
[LLM Dataset Generator]
 • 프롬프트 1: "이 문서를 바탕으로 실무자가 물어볼 법한 질문 3개를 생성하라"
 • 프롬프트 2: "제시된 본문만을 근거로 삼아 정답과 출처를 작성하라"
        │
        ▼
[품질 필터링 & 검수]
 • 환각 여부 및 문법 검증
 • 사용자 검수 UI (Human-in-the-loop)
        │
        ▼
[학습용 데이터셋 (JSONL)]
```

### ② 파인튜닝 데이터셋 예시 (`train.jsonl`)
```json
{
  "messages": [
    {"role": "system", "content": "당신은 사내 표준 지침과 보고서 양식을 준수하는 전문 AI 비서입니다."},
    {"role": "user", "content": "2025년 AI 세미나에서 언급된 Agentic RAG 도입 전략의 핵심 3가지를 개조식으로 요약해줘."},
    {"role": "assistant", "content": "2025년 AI 세미나 자료(Slide 5~7)에 명시된 핵심 전략은 다음과 같습니다:\n\n1. **KM 데이터 정제**: HWP 및 PPTX 발표자 노트를 포함한 구조화 전처리\n2. **하이브리드 검색**: BM25와 BGE-M3 임베딩 결합\n3. **자가 검증 루프**: LangGraph 기반의 질의 재작성 및 환각 평가기 도입"}
  ]
}
```

### ③ 학습 기법 선정
* **LoRA / QLoRA (권장)**: 모델 전체를 학습하지 않고 저랭크 어댑터(Low-Rank Adapter)만 튜닝하여 적은 GPU 자원(단일 RTX 3090/4090/A100)으로 빠른 학습 가능.
* **기반 베이스 모델**: Llama-3-8B-Instruct, Qwen2.5-7B/14B, Solar-10.7B 등.
