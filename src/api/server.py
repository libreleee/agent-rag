"""
Agentic RAG & KM 통합 FastAPI 서버
문서 업로드/파싱, HWP to PDF 즉시/폴더 일괄 변환, RAG 검색 엔드포인트 및 No-Code 웹 대시보드 제공
"""
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from src.core.config import settings
from src.parsers.unified_parser import UnifiedDocumentParser
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import HybridRetriever
from src.utils.hwp_to_pdf import convert_hwp_to_pdf
from src.utils.hwp_to_docx import convert_hwp_to_docx

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HWPX/PPTX/PDF 고품질 파싱, 한글(HWP) PDF 변환, Agentic RAG 파이프라인 API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = UnifiedDocumentParser()
indexer = KnowledgeIndexer(persist_dir=settings.VECTOR_DB_DIR)
retriever = HybridRetriever(persist_dir=str(settings.VECTOR_DB_DIR))

# Static UI directory
STATIC_DIR = Path(__file__).parent / "static"

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4

class SearchResponseItem(BaseModel):
    content: str
    metadata: dict
    score: float
    source: str

class FolderConvertRequest(BaseModel):
    input_folder: str
    output_folder: Optional[str] = None
    target_format: Optional[str] = "pdf"  # "pdf" or "docx"

@app.get("/", response_class=HTMLResponse)
def serve_web_ui():
    """
    No-Code 웹 대시보드 (HWP PDF/Word 변환, 폴더 일괄 변환, 지식 등록, 지식 검색)를 렌더링합니다.
    """
    index_html = STATIC_DIR / "index.html"
    if index_html.is_file():
        return HTMLResponse(content=index_html.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Agentic RAG & Converter Server Online</h1><p><a href='/docs'>Swagger API</a></p>")

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.post("/api/convert_hwp_to_pdf")
async def convert_hwp(file: UploadFile = File(...)):
    """
    업로드된 한글(.hwp, .hwpx) 문서를 PDF로 즉시 변환하여 다운로드합니다.
    """
    temp_dir = settings.DATA_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_path = temp_dir / file.filename
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        pdf_path = convert_hwp_to_pdf(str(input_path), output_dir=str(temp_dir))
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 변환 실패: {str(e)}")

@app.post("/api/convert_hwp_to_docx")
async def convert_hwp_word(file: UploadFile = File(...)):
    """
    업로드된 한글(.hwp, .hwpx) 문서를 Word (.docx)로 즉시 변환하여 다운로드합니다.
    """
    temp_dir = settings.DATA_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_path = temp_dir / file.filename
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        docx_path = convert_hwp_to_docx(str(input_path), output_dir=str(temp_dir))
        return FileResponse(
            path=str(docx_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=docx_path.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Word(.docx) 변환 실패: {str(e)}")

@app.post("/api/convert_folder")
def convert_folder_batch(req: FolderConvertRequest):
    """
    지정된 로컬 폴더의 모든 한글(.hwp, .hwpx, .doc) 파일을 PDF 또는 Word(.docx)로 일괄 변환하여 저장합니다.
    """
    in_dir = Path(req.input_folder.strip())
    if not in_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"입력 폴더를 찾을 수 없습니다: {req.input_folder}")

    target_fmt = (req.target_format or "pdf").lower()
    default_subfolder = "docx_output" if target_fmt == "docx" else "pdf_output"
    out_dir = Path(req.output_folder.strip()) if req.output_folder else (in_dir / default_subfolder)
    out_dir.mkdir(parents=True, exist_ok=True)

    supported_exts = {".hwp", ".hwpx", ".doc", ".docx"}
    files = [f for f in in_dir.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

    if not files:
        return {
            "success": True,
            "total": 0,
            "converted": 0,
            "failed": 0,
            "target_format": target_fmt,
            "message": "변환 대상 파일(.hwp, .hwpx)이 없습니다.",
            "output_folder": str(out_dir)
        }

    results = []
    success_count = 0
    fail_count = 0

    for f in files:
        try:
            if target_fmt == "docx":
                out_file = convert_hwp_to_docx(str(f), output_dir=str(out_dir))
            else:
                out_file = convert_hwp_to_pdf(str(f), output_dir=str(out_dir))
            results.append({"file": f.name, "status": "success", "converted_file": out_file.name})
            success_count += 1
        except Exception as e:
            results.append({"file": f.name, "status": "error", "error": str(e)})
            fail_count += 1

    return {
        "success": True,
        "total": len(files),
        "converted": success_count,
        "failed": fail_count,
        "target_format": target_fmt,
        "output_folder": str(out_dir),
        "details": results
    }

@app.post("/api/upload")
async def upload_and_index_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form("사내문서")
):
    """
    HWPX, PPTX, PDF 문서를 업로드 받아 고품질 파싱 후 지식 베이스(ChromaDB)에 인덱싱합니다.
    """
    save_path = settings.RAW_DATA_DIR / file.filename
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. 문서 고품질 파싱
        parsed_result = parser.parse(save_path)

        # 2. 파싱 결과 Markdown 파일로 보관
        processed_md_path = settings.PROCESSED_DATA_DIR / f"{file.filename}.md"
        processed_md_path.write_text(parsed_result["markdown"], encoding="utf-8")

        # 3. ChromaDB 하이브리드 인덱싱
        chunk_count = indexer.index_parsed_document(
            parsed_data=parsed_result,
            extra_metadata={"category": category}
        )

        return {
            "success": True,
            "filename": file.filename,
            "file_type": parsed_result.get("file_type"),
            "total_chunks_indexed": chunk_count,
            "char_count": parsed_result.get("char_count"),
            "message": f"문서 파싱 및 {chunk_count}개 지식 청크 인덱싱 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 처리 실패: {str(e)}")

@app.post("/api/search", response_model=List[SearchResponseItem])
def search_knowledge(req: SearchRequest):
    """
    하이브리드(Vector + BM25) 지식 검색을 수행합니다.
    """
    results = retriever.search(query=req.query, top_k=req.top_k)
    return results

@app.get("/api/status")
def get_knowledge_status():
    """
    현재 등록된 문서 및 저장소 통계를 반환합니다.
    """
    raw_files = list(settings.RAW_DATA_DIR.glob("*"))
    processed_files = list(settings.PROCESSED_DATA_DIR.glob("*.md"))
    
    return {
        "raw_documents_count": len(raw_files),
        "processed_markdown_count": len(processed_files),
        "raw_files": [f.name for f in raw_files]
    }

@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    """
    지식 베이스(ChromaDB), 원본 파일 및 파싱된 마크다운에서 문서를 완전히 삭제합니다.
    """
    deleted_chunks = indexer.delete_document(filename)

    # 원본 및 파싱 파일 삭제
    raw_path = settings.RAW_DATA_DIR / filename
    if raw_path.is_file():
        raw_path.unlink(missing_ok=True)

    md_path = settings.PROCESSED_DATA_DIR / f"{filename}.md"
    if md_path.is_file():
        md_path.unlink(missing_ok=True)

    return {
        "success": True,
        "filename": filename,
        "deleted_chunks": deleted_chunks,
        "message": f"문서 '{filename}' 및 {deleted_chunks}개 지식 청크 삭제 완료"
    }

