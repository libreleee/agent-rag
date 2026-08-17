"""
PDF 고품질 파서 (PyMuPDF 기반)
페이지별 레이아웃 및 텍스트/메타데이터 추출
"""
from pathlib import Path
from typing import Dict, Any, List
import pymupdf as fitz

class PdfParser:
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

        doc = fitz.open(str(path))
        pages_data = []

        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages_data.append({
                    "page_number": idx,
                    "markdown": f"## [Page {idx}]\n\n{text}"
                })

        full_markdown = "\n\n---\n\n".join([p["markdown"] for p in pages_data])

        return {
            "source_file": path.name,
            "file_type": "pdf",
            "total_pages": len(doc),
            "pages": pages_data,
            "markdown": full_markdown,
            "char_count": len(full_markdown)
        }
