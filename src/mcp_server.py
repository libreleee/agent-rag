"""
AI Agentic Knowledge Hub - Model Context Protocol (MCP) Server
Allows autonomous AI agents (Claude Desktop, Cursor, Antigravity, LangGraph, AutoGen)
to parse, convert, index, and retrieve enterprise documents via standard MCP tools.
"""
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.mcpserver import MCPServer
from src.core.config import settings
from src.parsers.unified_parser import UnifiedDocumentParser
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import HybridRetriever
from src.utils.hwp_to_pdf import convert_hwp_to_pdf
from src.utils.hwp_to_docx import convert_hwp_to_docx

# Initialize Unified Singletons
server = MCPServer(
    name="AI-Agentic-Knowledge-Hub",
    version="1.0.0",
    instructions=(
        "AI Agentic Knowledge Hub MCP Server. "
        "Provides tools for converting HWP/HWPX documents to PDF, parsing complex documents "
        "(with table preservation and speaker notes), indexing into knowledge mesh, "
        "and performing hybrid (Vector + BM25) knowledge retrieval."
    )
)

parser = UnifiedDocumentParser()
indexer = KnowledgeIndexer(persist_dir=settings.VECTOR_DB_DIR)
retriever = HybridRetriever(persist_dir=str(settings.VECTOR_DB_DIR))


@server.tool()
def convert_document(file_path: str, output_dir: Optional[str] = None) -> str:
    """Convert a Korean Hangul document (.hwp, .hwpx) or Office document to high-fidelity PDF.

    Args:
        file_path: Absolute or relative path to the input document (.hwp, .hwpx, .doc, .docx).
        output_dir: Optional output directory where the PDF should be saved.
                    Defaults to the same folder as the input file.

    Returns:
        JSON string containing conversion status and generated PDF path.
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return json.dumps({"success": False, "error": f"File not found: {file_path}"}, ensure_ascii=False)

        out_path = convert_hwp_to_pdf(str(path), output_dir=output_dir)
        return json.dumps({
            "success": True,
            "source_file": str(path),
            "pdf_path": str(out_path),
            "file_size_bytes": out_path.stat().st_size,
            "message": f"Successfully converted {path.name} to PDF."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def convert_document_to_word(file_path: str, output_dir: Optional[str] = None) -> str:
    """Convert a Korean Hangul document (.hwp, .hwpx) to a styled Word (.docx) document.

    Preserves headings, bullet points, and tables.

    Args:
        file_path: Path to the input document (.hwp, .hwpx, .doc, .txt, .md).
        output_dir: Optional destination folder. Defaults to input file's directory.

    Returns:
        JSON string containing conversion status and generated .docx file path.
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return json.dumps({"success": False, "error": f"File not found: {file_path}"}, ensure_ascii=False)

        out_path = convert_hwp_to_docx(str(path), output_dir=output_dir)
        return json.dumps({
            "success": True,
            "source_file": str(path),
            "docx_path": str(out_path),
            "file_size_bytes": out_path.stat().st_size,
            "message": f"Successfully converted {path.name} to Word (.docx)."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def parse_document(file_path: str) -> str:
    """Parse HWP, HWPX, PPTX, PDF, or Word documents into lossless structured Markdown.

    Preserves tables (as Markdown tables) and presentation speaker notes.

    Args:
        file_path: Path to the document file.

    Returns:
        JSON string containing structured markdown, file metadata, and character count.
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return json.dumps({"success": False, "error": f"File not found: {file_path}"}, ensure_ascii=False)

        result = parser.parse(path)
        return json.dumps({
            "success": True,
            "source_file": result.get("source_file"),
            "file_type": result.get("file_type"),
            "engine_used": result.get("engine_used", "unified_parser"),
            "char_count": result.get("char_count"),
            "markdown": result.get("markdown")
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def search_knowledge(query: str, top_k: int = 4) -> str:
    """Perform hybrid (ChromaDB Vector + BM25 Lexical with RRF) search on the knowledge base.

    Args:
        query: Natural language query or keywords.
        top_k: Number of most relevant document chunks to return (default: 4).

    Returns:
        JSON string containing ranked search result chunks, similarity scores, and sources.
    """
    try:
        results = retriever.search(query=query, top_k=top_k)
        return json.dumps({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def index_document(file_path: str, category: str = "사내문서") -> str:
    """Parse and index a document into the ChromaDB vector & BM25 hybrid knowledge base.

    Args:
        file_path: Path to the document (.hwpx, .pptx, .pdf, .md, .txt, .hwp).
        category: Category or tag for metadata classification (e.g., '규정', '매뉴얼', '보고서').

    Returns:
        JSON string containing indexing status and number of created chunks.
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return json.dumps({"success": False, "error": f"File not found: {file_path}"}, ensure_ascii=False)

        parsed_result = parser.parse(path)
        chunk_count = indexer.index_parsed_document(
            parsed_data=parsed_result,
            extra_metadata={"category": category}
        )
        return json.dumps({
            "success": True,
            "filename": path.name,
            "file_type": parsed_result.get("file_type"),
            "total_chunks_indexed": chunk_count,
            "char_count": parsed_result.get("char_count"),
            "message": f"Successfully indexed {path.name} into knowledge base ({chunk_count} chunks)."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def delete_document(file_name: str) -> str:
    """Delete a document and all its indexed chunks from ChromaDB and the knowledge base.

    Args:
        file_name: Name of the source file to remove (e.g., '모집공고.hwp').

    Returns:
        JSON string containing deletion status and number of removed chunks.
    """
    try:
        deleted_count = indexer.delete_document(file_name)
        raw_path = settings.RAW_DATA_DIR / file_name
        if raw_path.is_file():
            raw_path.unlink(missing_ok=True)
        md_path = settings.PROCESSED_DATA_DIR / f"{file_name}.md"
        if md_path.is_file():
            md_path.unlink(missing_ok=True)

        return json.dumps({
            "success": True,
            "file_name": file_name,
            "deleted_chunks": deleted_count,
            "message": f"Successfully deleted {file_name} and {deleted_count} chunks from knowledge base."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def batch_convert_folder(input_folder: str, output_folder: Optional[str] = None, target_format: str = "pdf") -> str:
    """Batch convert all Hangul (.hwp, .hwpx) documents in a directory to PDF or Word (.docx).

    Args:
        input_folder: Folder containing source documents.
        output_folder: Destination folder (defaults to input_folder/pdf_output or input_folder/docx_output).
        target_format: Target format: 'pdf' (default) or 'docx'.

    Returns:
        JSON string with batch conversion summary and per-file results.
    """
    try:
        in_path = Path(input_folder)
        if not in_path.is_dir():
            return json.dumps({"success": False, "error": f"Directory not found: {input_folder}"}, ensure_ascii=False)

        fmt = target_format.lower()
        default_sub = "docx_output" if fmt == "docx" else "pdf_output"
        out_path = Path(output_folder) if output_folder else (in_path / default_sub)
        out_path.mkdir(parents=True, exist_ok=True)

        supported_exts = {".hwp", ".hwpx", ".doc", ".docx"}
        files = [f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

        results = []
        success_count = 0
        fail_count = 0

        for f in files:
            try:
                if fmt == "docx":
                    res_file = convert_hwp_to_docx(str(f), output_dir=str(out_path))
                else:
                    res_file = convert_hwp_to_pdf(str(f), output_dir=str(out_path))
                results.append({"file": f.name, "status": "success", "converted_file": res_file.name})
                success_count += 1
            except Exception as e:
                results.append({"file": f.name, "status": "error", "error": str(e)})
                fail_count += 1

        return json.dumps({
            "success": True,
            "input_folder": str(in_path),
            "output_folder": str(out_path),
            "target_format": fmt,
            "total_files": len(files),
            "converted": success_count,
            "failed": fail_count,
            "details": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@server.tool()
def get_system_status() -> str:
    """Retrieve the current statistics of the AI Agentic Knowledge Hub.

    Returns:
        JSON string with raw documents count, processed markdown count, and list of files.
    """
    try:
        raw_files = list(settings.RAW_DATA_DIR.glob("*"))
        processed_files = list(settings.PROCESSED_DATA_DIR.glob("*.md"))
        return json.dumps({
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "raw_documents_count": len(raw_files),
            "processed_markdown_count": len(processed_files),
            "raw_files": [f.name for f in raw_files]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def main():
    """Run the MCP server over standard I/O (stdio)."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
