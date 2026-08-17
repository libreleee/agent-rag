"""
통합 문서 파서 (Unified Document Parser)
확장자(.hwpx, .hwp, .pptx, .pdf, .txt, .md)에 따라 최적의 고품질 파서로 자동 라우팅
"""
from pathlib import Path
from typing import Dict, Any

from .hwpx_parser import HwpxParser
from .pptx_parser import PptxParser
from .pdf_parser import PdfParser
from .hwp_parser import HwpDualEngineParser

class UnifiedDocumentParser:
    def __init__(self):
        self.hwpx_parser = HwpxParser()
        self.hwp_dual_parser = HwpDualEngineParser()
        self.pptx_parser = PptxParser()
        self.pdf_parser = PdfParser()

    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".hwpx":
            # 1순위: HwpxParser (Pure XML), 실패 시 HwpDualEngineParser
            try:
                return self.hwpx_parser.parse(path)
            except Exception:
                return self.hwp_dual_parser.parse(path)
        elif ext == ".hwp":
            # HWP 바이너리: rhwp + LibreOffice 듀얼 엔진 하이브리드 파싱
            return self.hwp_dual_parser.parse(path)
        elif ext in [".pptx", ".ppt"]:
            return self.pptx_parser.parse(path)
        elif ext == ".pdf":
            return self.pdf_parser.parse(path)
        elif ext in [".md", ".txt"]:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return {
                "source_file": path.name,
                "file_type": ext.replace(".", ""),
                "markdown": content,
                "char_count": len(content)
            }
        else:
            raise ValueError(f"지원하지 않는 문서 형식입니다: {ext}")
