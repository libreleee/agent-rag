# 2026년도 AI 에이전트 도입 및 KM 운영 규정

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
