# 📊 03. 프레젠테이션 (PPTX / PPT) 슬라이드 & 발표자 노트 파싱 가이드

본 문서는 세미나 발표 자료, 사업 기획서, 교육 교안 등 PPTX 문서를 **AI Agentic Knowledge Hub**에 고품질로 인덱싱하기 위한 기술 가이드입니다.

---

## 1. PPTX 포맷의 핵심 특징: "발표자 노트(Speaker Notes)의 중요성"

* 프레젠테이션 슬라이드 화면에는 핵심 키워드나 요약 문장만 들어가지만, **진짜 중요한 세부 맥락, 수치, 설명은 슬라이드 하단의 '발표자 메모(Speaker Notes)'에 존재**합니다.
* 일반적인 RAG 파서가 슬라이드 화면 텍스트만 긁어모으면 지식의 60% 이상이 유실됩니다.
* **AI Agentic Knowledge Hub는 슬라이드 본문 + 표 + 도형 텍스트 + 발표자 메모를 하나로 통합하여 완벽한 맥락을 보존**합니다.

---

## 2. 사용 도구 및 파서

* **`python-pptx`**: 슬라이드 구조, 텍스트 박스, 표(Shape Type: Table), 발표자 메모(`slide.notes_slide.notes_text_frame`) 객체 접근
* **LibreOffice Headless**: 구형 `.ppt` 바이너리 파일 수신 시 최신 `.pptx` 또는 `.pdf`로 자동 변환 후 파싱

---

## 3. 구조화 전처리 및 마크다운 출력 규격

각 슬라이드를 독립된 의미 단위(Document Chunk)로 분리하고 아래 포맷으로 구조화합니다:

```markdown
## Slide 5: 2026년 AI 에이전트 구축 전략

### [슬라이드 본문]
* **핵심 과제**: RAG와 Agent Tool의 단일 Hub 통합
* **목표 아키텍처**: Model Context Protocol(MCP) 표준 채택
* **예상 ROI**: 문서 처리 시간 80% 단축

### [표 데이터]
| 구분 | 2025년 | 2026년 목표 |
| --- | --- | --- |
| 자동화율 | 30% | 85% |
| 처리 속도 | 분 단위 | 초 단위 |

### [발표자 메모 (Speaker Notes)]
> 본 슬라이드에서는 기존 분리형 아키텍처의 한계를 강조할 것. 
> 특히 사내 보안 규정상 외부 SaaS를 쓸 수 없는 환경에서 로컬 LibreOffice 기반 HWP 변환 엔진과 결합된 온프레미스 Hub의 강점을 전달할 것.
```

---

## 4. Hub 등록 및 활용

* **청킹 단위**: 슬라이드 1장 = 1개 기본 청크 (필요 시 본문과 노트를 부모-자식 관계로 링크)
* **메타데이터**:
  ```json
  {
    "source": "2026_AI_전략세미나.pptx",
    "file_type": "pptx",
    "slide_number": 5,
    "has_notes": true,
    "has_tables": true
  }
  ```
