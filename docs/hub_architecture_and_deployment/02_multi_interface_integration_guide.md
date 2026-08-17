# 🌐 02. 다중 인터페이스 실행 및 외부 연동 가이드
*(Web, Mobile, Desktop GUI, REST API, MCP Server, Python SDK)*

본 문서는 구축된 **AI Agentic Knowledge Hub**를 실행하고, **인간 사용자(GUI/Web)와 다양한 외부 플랫폼(앱, 웹, SaaS, AI 에이전트)**에서 호출하는 구체적인 코드와 설정 방법을 설명합니다.

---

## 🚀 1. 허브 실행 방법 (3대 실행 모드)

### 모드 A. 🌐 웹 대시보드 & REST API 서버 실행 (추천)
모바일 앱, 프론트엔드 웹, 사내 시스템 연동 및 웹 GUI를 제공합니다.
```bash
# 개발 모드 (코드 변경 시 자동 재시작)
uv run uvicorn src.api.server:app --port 8001 --reload

# 상용 프로덕션 모드 (백그라운드 다중 워커)
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8001 --workers 4
```
* **웹 대시보드 URL**: `http://localhost:8001/`
* **Swagger/OpenAPI 명세서**: `http://localhost:8001/docs`

---

### 모드 B. 💻 윈도우 원클릭 데스크톱 GUI 실행
터미널 없이 윈도우 탐색기 창으로 폴더를 선택하여 문서를 일괄 변환합니다.
* **실행 방법**: [`run_gui.bat`](file:///e:/work/ai/agent/agent-rag/run_gui.bat) 파일 더블 클릭  
  *(또는 `uv run python gui_converter.py`)*

---

### 모드 C. 🤖 AI 에이전트 전용 MCP Server 실행
Claude Desktop, Cursor, Antigravity 등의 에이전트와 Stdio로 통신합니다.
* **실행 방법**: [`run_mcp_server.bat`](file:///e:/work/ai/agent/agent-rag/run_mcp_server.bat) 실행  
  *(또는 `uv run python src/mcp_server.py`)*

---

## 💻 2. 외부 플랫폼별 실제 호출 코드 예제

### 1) 🌐 웹 프론트엔드 (React / Next.js / Vue / Vanilla JS)

#### A. 한글 파일 PDF 변환 및 다운로드
```javascript
async function convertHwpToPdf(fileInput) {
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  const response = await fetch('http://localhost:8001/api/convert_hwp_to_pdf', {
    method: 'POST',
    body: formData
  });

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = 'converted.pdf';
  a.click();
}
```

#### B. 하이브리드 지식 검색 질의
```javascript
async function searchKnowledge(queryText) {
  const response = await fetch('http://localhost:8001/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: queryText, top_k: 4 })
  });

  const results = await response.json();
  console.log("검색된 문서 청크 리스트:", results);
}
```

---

### 2) 📱 모바일 앱 / 타 백엔드 (Python `requests` / Java / C#)

#### A. 문서 지식 베이스 업로드 및 인덱싱
```python
import requests

url = "http://localhost:8001/api/upload"
files = {"file": open("2026_신규사업계획서.hwpx", "rb")}
data = {"category": "기획문서"}

resp = requests.post(url, files=files, data=data)
print(resp.json())
# 반환: {'success': True, 'total_chunks_indexed': 15, 'char_count': 12400, ...}
```

#### B. 로컬 폴더 일괄 변환 요청
```python
import requests

url = "http://localhost:8001/api/convert_folder"
payload = {
    "input_folder": "C:/Users/Documents/한글문서모음",
    "output_folder": "C:/Users/Documents/PDF출력"
}

resp = requests.post(url, json=payload)
print(resp.json())
```

---

### 3) 🤖 AI 에이전트 연동 (Claude Desktop / Cursor / Antigravity)

에이전트 설정 파일(`claude_desktop_config.json` 또는 `mcp_config.json`)에 아래 블록을 추가합니다:

```json
{
  "mcpServers": {
    "ai-agentic-knowledge-hub": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "E:\\work\\ai\\agent\\agent-rag",
        "src/mcp_server.py"
      ]
    }
  }
}
```

**에이전트와의 실제 대화 예시**:
* *"이 프로젝트의 data/raw 폴더에 있는 문서 내용 중 보안 관리자 책임 조항 찾아줘."*  
  ➔ 에이전트가 `search_knowledge` 도구를 자동 호출하여 정확한 본문 인용 후 답변.

---

### 4) 📦 파이썬 코드 내 직접 SDK 임포트 방식 (No HTTP)

별도의 웹 서버 가동 없이 파이썬 배치 스크립트나 데이터 분석 노트북에서 직접 가져다 쓰는 방법:

```python
from src.parsers.unified_parser import UnifiedDocumentParser
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import HybridRetriever
from src.utils.hwp_to_pdf import convert_hwp_to_pdf

# 1. HWP -> PDF 변환
pdf_path = convert_hwp_to_pdf("report.hwp", output_dir="./output")

# 2. 문서 무손실 파싱
parser = UnifiedDocumentParser()
parsed_data = parser.parse("report.hwpx")

# 3. ChromaDB 지식 인덱싱
indexer = KnowledgeIndexer()
indexer.index_parsed_document(parsed_data, extra_metadata={"category": "사내문서"})

# 4. 하이브리드 지식 검색
retriever = HybridRetriever()
results = retriever.search("핵심 키워드 질문", top_k=3)
for item in results:
    print(f"[{item['source']}] (Score: {item['score']:.4f})\n{item['content']}\n")
```
