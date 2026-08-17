"""
파이프라인 동작 검증 테스트 스크립트
가상 Markdown/텍스트 문서를 생성하여 파싱 -> 인덱싱 -> 하이브리드 검색 테스트
"""
from pathlib import Path
from src.parsers.unified_parser import UnifiedDocumentParser
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import HybridRetriever
from src.core.config import settings

def run_test():
    print("=== 1. 테스트 샘플 문서 생성 ===")
    sample_path = settings.RAW_DATA_DIR / "sample_policy.md"
    sample_content = """# 2026년도 AI 에이전트 도입 및 KM 운영 규정

## 제1조 (목적)
본 규정은 사내 모든 비정형 문서(HWPX, PPTX, PDF)를 지식 자산(KM)으로 구조화하고, Agentic RAG 시스템을 통해 안전하고 신속하게 활용하는 것을 목적으로 한다.

## 제2조 (표 데이터 처리 및 지원 포맷)
1. HWPX 문서는 XML 네임스페이스 파서를 통해 표의 병합 셀(colspan, rowspan)을 2D 매트릭스 Markdown Table로 완벽 보존한다.
2. 세미나 PPTX 문서는 슬라이드 본문뿐만 아니라 발표자 노트(Speaker Notes)를 반드시 통합 추출한다.

| 문서 포맷 | 파싱 엔진 | 주요 특징 |
| --- | --- | --- |
| HWPX | Pure Python XML Parser | 한글 미설치 환경 100% 표 복원 |
| PPTX | Python-pptx | 슬라이드 + 발표자 메모 통합 |
| PDF | PyMuPDF / Docling | 다단 레이아웃 및 텍스트 추출 |

## 제3조 (하이브리드 검색 기준)
검색 시스템은 Dense Vector 임베딩(0.6 가중치)과 Sparse BM25 키워드 점수(0.4 가중치)를 융합한 RRF 하이브리드 검색을 기본으로 수행한다.
"""
    sample_path.write_text(sample_content, encoding="utf-8")
    print(f"-> 샘플 생성 완료: {sample_path}")

    print("\n=== 2. 통합 파서 테스트 ===")
    parser = UnifiedDocumentParser()
    parsed = parser.parse(sample_path)
    print(f"-> 파싱 성공! 파일타입: {parsed['file_type']}, 글자수: {parsed['char_count']}")

    print("\n=== 3. ChromaDB 인덱서 청킹 및 저장 ===")
    indexer = KnowledgeIndexer(persist_dir=settings.VECTOR_DB_DIR)
    chunk_count = indexer.index_parsed_document(parsed, extra_metadata={"category": "사내규정"})
    print(f"-> 인덱싱 완료! 총 {chunk_count}개 청크 저장됨.")

    print("\n=== 4. 하이브리드(Vector + BM25) 지식 검색 테스트 ===")
    retriever = HybridRetriever(persist_dir=str(settings.VECTOR_DB_DIR))
    queries = [
        "HWPX 표는 어떻게 파싱해?",
        "PPTX 세미나 자료에서 발표자 메모도 나오나?",
        "하이브리드 검색 가중치 비율은?"
    ]

    for q in queries:
        print(f"\n[질의]: {q}")
        results = retriever.search(q, top_k=1)
        for r in results:
            print(f"  [유사도 점수]: {r['score']}")
            print(f"  [검색된 본문 내용]:\n{r['content'][:150]}...")

    print("\n=== 모든 테스트가 성공적으로 완료되었습니다! ===")

if __name__ == "__main__":
    run_test()
