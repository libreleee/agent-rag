# 05. A2A 프로토콜 및 허브 레지스트리

> **선행 의존성**: [02_knowledge_store_abstraction.md](./02_knowledge_store_abstraction.md)
> (02번 완료 후 03·04번과 **병렬 진행 가능**)

---

## 1. 현재 상태 (As-Is)

### 1.1 이미 되어 있는 것

프로젝트명이 "AI Agentic Knowledge Hub"인 만큼, 재사용 구조의 상당 부분은
실제로 구현되어 있습니다.

**MCP 서버** (`src/mcp_server.py`) — stdio 전송 방식의 정식 MCP 서버로,
다음 7개 도구를 노출합니다.

| 도구 | 기능 |
| :--- | :--- |
| `convert_document` | HWP/HWPX ➔ PDF |
| `convert_document_to_word` | HWP/HWPX ➔ DOCX |
| `parse_document` | 구조화 마크다운 파싱 |
| `search_knowledge` | 지식 검색 |
| `index_document` | 지식 베이스 등록 |
| `batch_convert_folder` | 폴더 일괄 변환 |
| `get_system_status` | 시스템 상태 |

`mcp_config.json`에 등록되어 있어 Claude Desktop, Cursor 등 MCP를 지원하는
클라이언트에서 그대로 사용할 수 있습니다.

**REST API** (`src/api/server.py`) — 동일 기능을 HTTP로도 노출하여,
MCP를 지원하지 않는 시스템도 연동 가능합니다.

### 1.2 없는 것

**A2A(Agent-to-Agent) 프로토콜** — 코드 전체를 검색한 결과 관련 구현이 없습니다.
Agent Card(`.well-known/agent.json`), 스킬 디스커버리, 태스크 수명주기 관리가 모두
부재합니다.

**허브 레지스트리** — 여러 MCP/A2A 서버를 중앙에서 등록하고 조회하는 기능이 없습니다.

### 1.3 "허브"라는 이름과 실제 구조의 차이

현재 연결 방식은 다음과 같습니다.

```
[프로젝트 A] ──mcp_config.json 개별 등록──┐
[프로젝트 B] ──mcp_config.json 개별 등록──┼──> 이 서버
[프로젝트 C] ──mcp_config.json 개별 등록──┘
```

즉 **각 클라이언트가 개별 설정으로 이 서버에 직접 연결하는** 방식입니다.
"중앙 허브를 통해 여러 프로젝트가 능력을 발견하고 찾아 붙는" 구조가 아닙니다.

문제점:

- 서버 주소/경로가 바뀌면 **모든 클라이언트 설정을 각각 수정**해야 함
- 어떤 능력(도구)이 존재하는지 알려면 소스를 직접 읽어야 함
- 여러 지식 허브를 운영할 때 클라이언트가 어느 것에 물어야 할지 판단 불가
- 에이전트가 **다른 에이전트에게 작업을 위임**할 수 없음 (MCP는 도구 호출 모델)

### 1.4 MCP와 A2A의 역할 구분

두 프로토콜은 경쟁 관계가 아니라 **계층이 다릅니다.**

| 구분 | MCP | A2A |
| :--- | :--- | :--- |
| 관계 | 에이전트 ➔ **도구** | 에이전트 ➔ **에이전트** |
| 호출 | 동기적 함수 호출 | 태스크 위임 (장시간 실행 가능) |
| 상태 | 무상태 | 태스크 수명주기 (submitted ➔ working ➔ completed) |
| 발견 | 클라이언트 설정에 사전 등록 | Agent Card로 런타임 발견 |

본 프로젝트는 **둘 다 필요합니다.**
"HWP를 PDF로 변환"은 도구 호출(MCP)이지만,
"이 폴더의 문서들을 분석해 학습 데이터셋을 만들어 달라"는 시간이 걸리는
태스크 위임(A2A)입니다. 04번의 데이터셋 생성이 대표적인 A2A 대상입니다.

---

## 2. 목표 상태 (To-Be)

```
                    ┌─────────────────────────────┐
                    │      Hub Registry            │
                    │  능력 카탈로그 / 검색 / 헬스   │
                    └──────────┬──────────────────┘
                     등록 │           │ 조회
            ┌─────────────┴───┐   ┌───┴──────────────┐
            ▼                 ▼   ▼                  ▼
   ┌──────────────┐  ┌──────────────┐      ┌──────────────┐
   │ Knowledge Hub│  │  타 에이전트  │      │  클라이언트   │
   │  (본 프로젝트)│  │              │      │  프로젝트     │
   └──────┬───────┘  └──────────────┘      └──────────────┘
          │
   ┌──────┴───────────────────────┐
   │  MCP  │  REST  │  A2A [신규] │   ← 동일 코어의 3중 노출
   └──────────────────────────────┘
                │
                ▼
      KnowledgeStore (02번) / DatasetBuilder (04번)
```

**중요 원칙**: A2A는 **새 기능이 아니라 새 노출 방식**입니다.
비즈니스 로직을 서비스 계층으로 한 번 정리하면, MCP·REST·A2A가 모두 그것을
얇게 감싸는 구조가 됩니다. 지금은 로직이 MCP 핸들러와 REST 핸들러에
**중복 구현**되어 있습니다(예: `batch_convert_folder`와 `convert_folder_batch`가
거의 동일한 코드).

---

## 3. 서비스 계층 선행 정리

A2A를 붙이기 전에 3중 중복을 막기 위한 정리가 필요합니다.

```
src/services/
├── conversion_service.py     # 변환 로직
├── knowledge_service.py      # 파싱/인덱싱/검색 (02번 KnowledgeStore 사용)
└── dataset_service.py        # 데이터셋 생성 (04번)
```

```
src/mcp_server.py   ──┐
src/api/server.py   ──┼──> src/services/*   ──> 코어 (parsers/rag/knowledge)
src/a2a_server.py   ──┘
```

이 정리를 하지 않고 A2A를 추가하면 동일 로직이 **세 벌**이 됩니다.

---

## 4. A2A 구현 설계

### 4.1 Agent Card

`GET /.well-known/agent.json`으로 자신의 능력을 공개합니다.

```json
{
  "name": "AI Agentic Knowledge Hub",
  "description": "한국어 문서(HWP/HWPX/PDF/PPTX) 파싱·변환·지식화 및 학습 데이터 생성 에이전트",
  "version": "1.0.0",
  "url": "http://localhost:8000/a2a",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "defaultInputModes": ["text", "file"],
  "defaultOutputModes": ["text", "file"],
  "skills": [
    {
      "id": "convert_hangul_document",
      "name": "한글 문서 변환",
      "description": "HWP/HWPX 문서를 표 구조를 보존하여 PDF 또는 Word로 변환합니다.",
      "tags": ["hwp", "hwpx", "pdf", "docx", "korean"],
      "examples": ["이 공고문 HWP를 표 유지해서 Word로 바꿔줘"]
    },
    {
      "id": "search_knowledge",
      "name": "지식 검색",
      "description": "등록된 문서에서 하이브리드(벡터+키워드) 검색을 수행합니다.",
      "tags": ["rag", "search"]
    },
    {
      "id": "build_training_dataset",
      "name": "학습 데이터셋 생성",
      "description": "지식 베이스로부터 SFT/QA/임베딩 학습 데이터셋을 생성합니다.",
      "tags": ["training", "dataset", "ml"]
    }
  ]
}
```

`description`과 `examples`가 중요합니다. 다른 에이전트가 **자연어로 판단**하여
이 에이전트에게 작업을 위임할지 결정하는 근거가 되기 때문입니다.

### 4.2 태스크 수명주기

문서 일괄 변환이나 데이터셋 생성은 수 분이 걸릴 수 있으므로 비동기 처리가 필수입니다.

```
submitted ──> working ──> completed
                 │           
                 ├──> input-required   (예: 출력 폴더 지정 필요)
                 ├──> failed
                 └──> canceled
```

| 엔드포인트 | 기능 |
| :--- | :--- |
| `POST /a2a/tasks/send` | 태스크 생성 |
| `POST /a2a/tasks/sendSubscribe` | 태스크 생성 + SSE 스트리밍 |
| `GET /a2a/tasks/{id}` | 상태 조회 |
| `POST /a2a/tasks/{id}/cancel` | 취소 |

태스크 상태는 `data/a2a/tasks/`에 영속화하여 서버 재시작 후에도 조회 가능하게 합니다.

### 4.3 스트리밍 진행률

`gui_converter.py`가 이미 파일별 진행률을 계산하고 있으므로
(`self.progress["value"] = (idx / total) * 100`), 동일한 정보를 SSE 이벤트로
내보내면 됩니다. 서비스 계층으로 정리할 때 진행률 콜백을 인자로 받도록 하면
GUI·A2A가 같은 코드를 공유할 수 있습니다.

---

## 5. 허브 레지스트리 설계

### 5.1 범위 결정

풀스케일 분산 레지스트리(Consul/etcd)는 현 단계에 과합니다.
**파일 기반 카탈로그 + 조회 API**로 시작합니다.

```
data/registry/
├── agents/
│   └── {agent_id}.json     # 등록된 에이전트의 Agent Card 사본
└── catalog.json             # 통합 능력 카탈로그
```

### 5.2 API

| 엔드포인트 | 기능 |
| :--- | :--- |
| `POST /registry/agents` | 에이전트 등록 (Agent Card URL 제출) |
| `GET /registry/agents` | 등록 목록 |
| `GET /registry/skills?q=...` | **능력 기반 검색** (핵심) |
| `DELETE /registry/agents/{id}` | 등록 해제 |
| `GET /registry/health` | 등록 에이전트 헬스 체크 |

`GET /registry/skills?q=한글 문서 변환`이 핵심 가치입니다.
클라이언트가 **어느 서버에 물어야 할지 모른 채로** 필요한 능력을 검색할 수 있습니다.

### 5.3 자기 등록

기동 시 자신의 Agent Card를 레지스트리에 등록합니다.

```python
REGISTRY_URL: str | None = None      # 미설정 시 등록 생략 (단독 실행 가능)
AGENT_PUBLIC_URL: str = "http://localhost:8000"
SELF_REGISTER: bool = False
```

기본값을 비활성으로 두어 **레지스트리 없이도 지금처럼 단독 동작**하게 합니다.

### 5.4 능력 검색에 자체 RAG 재사용

`GET /registry/skills?q=...`의 검색은 스킬 `description`/`examples`/`tags`를
색인하여 수행합니다. 이때 **본 프로젝트가 이미 가진 하이브리드 검색기(03번)를
그대로 재사용**할 수 있습니다.

스킬 설명은 짧고 고유명사가 많으므로 BM25 축이, 자연어 의도 매칭은 벡터 축이
담당합니다. 03번에서 BM25를 독립 축으로 만드는 개선이 여기서도 그대로 효과를 냅니다.

---

## 6. 보안 고려사항

현재 REST API에는 인증이 없고 CORS가 전면 개방되어 있습니다.

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

로컬 단독 사용 시에는 문제가 없으나, **레지스트리에 등록하여 외부에서 접근
가능해지는 순간 위험**해집니다. 특히 다음 엔드포인트는 임의 경로를 인자로 받습니다.

- `/api/convert_folder` — 임의 폴더 경로를 읽고 씀
- MCP `batch_convert_folder` — 동일

| 조치 | 우선순위 |
| :--- | :--- |
| API Key 인증 (`X-API-Key`) | 외부 노출 시 필수 |
| CORS 허용 출처 명시 | 외부 노출 시 필수 |
| 파일 경로 화이트리스트 (허용 디렉토리 제한) | 외부 노출 시 필수 |
| 레지스트리 등록 시 토큰 검증 | 권장 |
| 요청 속도 제한 | 권장 |

**A2A/레지스트리 작업과 보안 조치는 반드시 함께 진행합니다.**
네트워크 노출 기능만 먼저 만들고 보안을 뒤로 미루면 안 됩니다.

---

## 7. 작업 항목

| # | 작업 | 산출물 | 선행 |
| :--- | :--- | :--- | :--- |
| 1 | 서비스 계층 추출 (MCP/REST 중복 제거) | `src/services/` | 02 |
| 2 | 인증 및 경로 화이트리스트 | `src/core/security.py` | - |
| 3 | Agent Card 생성 | `src/a2a/card.py` | 1 |
| 4 | 태스크 저장소 + 수명주기 | `src/a2a/tasks.py` | 1 |
| 5 | A2A 엔드포인트 (send/get/cancel) | `src/a2a/server.py` | 3, 4 |
| 6 | SSE 스트리밍 | `src/a2a/streaming.py` | 5 |
| 7 | 레지스트리 저장소 + API | `src/registry/` | 3 |
| 8 | 자기 등록 클라이언트 | `src/registry/client.py` | 7 |
| 9 | 능력 검색 (03번 검색기 재사용) | `src/registry/search.py` | 7, 03 |
| 10 | 연동 가이드 문서 | `docs/hub_architecture_and_deployment/` | 5, 7 |

**1번과 2번을 먼저 하는 이유**: 서비스 계층 없이 A2A를 얹으면 로직이 세 벌이 되고,
보안 없이 네트워크 노출 기능을 만들면 취약한 상태로 배포될 위험이 있습니다.

---

## 8. 완료 판정 기준

- [ ] `/.well-known/agent.json`으로 능력이 공개된다
- [ ] 장시간 작업이 태스크로 위임되고 진행률이 스트리밍된다
- [ ] 서버 재시작 후에도 태스크 상태를 조회할 수 있다
- [ ] 레지스트리에서 능력 기반 자연어 검색으로 이 에이전트가 발견된다
- [ ] 레지스트리 미설정 시에도 단독 동작한다 (하위 호환)
- [ ] 동일 로직이 MCP/REST/A2A에 중복 구현되어 있지 않다
- [ ] 인증 없이 임의 파일 경로에 접근할 수 없다
