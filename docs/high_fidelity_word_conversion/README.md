# 📑 고품질 Word (.docx) 변환 기술 문서

본 디렉터리는 **한글(HWP/HWPX), PDF, PPTX 등 다양한 형식의 문서를 원본 서식과 표(Table) 격자 손실 없이 고품질 Word(`.docx`) 문서로 변환**하기 위해 개발된 레이아웃 역공학 엔진의 기술 명세 및 가이드를 담고 있습니다.

---

## 📚 문서 목차

* **[📝 01. 한글 (HWP/HWPX) ➔ 고품질 Word (.docx) 레이아웃 역공학 복원 기술 분석](./01_hwp_to_docx_layout_reconstruction.md)**
  - 기존 텍스트 추출 방식의 품질 한계 분석
  - `rhwp` (Rust 벡터 렌더러) + `pdf2docx` (위상 역공학 빌더) 2단계 하이브리드 파이프라인
  - **파이프라인 실행 우선순위(Priority Order) 설계와 품질 저하 방지 사례 분석**
  - **사람용(시각 재현) vs 기계용(RAG/학습 데이터) 분리 원칙 및 4단계 보완 로드맵**
  - 기존 방식 vs LibreOffice vs 2단계 하이브리드 엔진 비교 벤치마크
  - 핵심 파이썬 소스코드(`src/utils/hwp_to_docx.py`) 구조 및 다중 인터페이스 연동
