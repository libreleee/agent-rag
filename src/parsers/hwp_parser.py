"""
고품질 한글(HWP / HWPX) 듀얼 엔진 하이브리드 파서
1차: rhwp-python ➔ HWPX 정규화 ➔ HwpxParser (표/셀 구조 보존)
2차: rhwp extract_text (표를 순회하지 않는 평문 추출, 최후 수단)
3차 (Fallback): LibreOffice Headless ➔ PDF ➔ PyMuPDF 앙상블 파서
"""
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
import logging

from src.utils.hwp_to_pdf import convert_hwp_to_pdf
from .pdf_parser import PdfParser
from .hwpx_parser import HwpxParser

logger = logging.getLogger(__name__)


class HwpDualEngineParser:
    def __init__(self):
        self.pdf_parser = PdfParser()
        self.hwpx_parser = HwpxParser()

    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

        # 1차 시도: rhwp로 HWPX(개방형 XML)로 정규화한 뒤 구조 파서로 표까지 복원.
        # rhwp.extract_text()는 표 셀 내부를 순회하지 않아 양식 문서의 본문 대부분을
        # 유실하므로, 표 구조를 보존하는 이 경로를 최우선으로 시도한다.
        try:
            import rhwp
            doc = rhwp.parse(str(path))

            tmp_dir = Path(tempfile.mkdtemp(prefix="hwpx_norm_"))
            try:
                hwpx_path = tmp_dir / (path.stem + ".hwpx")
                doc.export_hwpx(str(hwpx_path))

                result = self.hwpx_parser.parse(hwpx_path)
                markdown_content = result.get("markdown", "")

                if markdown_content and len(markdown_content.strip()) > 20:
                    result.update({
                        "source_file": path.name,
                        "file_type": path.suffix.lower().replace(".", ""),
                        "engine_used": "rhwp-hwpx-structured",
                        "section_count": getattr(doc, "section_count", 1),
                        "paragraph_count": getattr(doc, "paragraph_count", 0),
                    })
                    logger.info(
                        f"[rhwp➔hwpx] 구조 파싱 성공: {path.name} "
                        f"(표 {result.get('table_count', 0)}개, {result.get('char_count', 0)}자)"
                    )
                    return result
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"rhwp HWPX 정규화 파싱 실패 ({e}). 평문 추출로 전환합니다.")

        # 2차 시도: rhwp 평문 추출 (표 내용은 유실되지만 본문만 있는 문서에는 충분)
        try:
            import rhwp
            doc = rhwp.parse(str(path))
            text = doc.extract_text()

            if text and len(text.strip()) > 20:
                # 문단 정리 및 마크다운 정규화
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                markdown_content = f"# {path.name}\n\n" + "\n\n".join(lines)

                return {
                    "source_file": path.name,
                    "file_type": path.suffix.lower().replace(".", ""),
                    "engine_used": "rhwp-rust-core",
                    "section_count": getattr(doc, "section_count", 1),
                    "paragraph_count": getattr(doc, "paragraph_count", len(lines)),
                    "markdown": markdown_content,
                    "char_count": len(markdown_content)
                }
        except Exception as e:
            logger.warning(f"rhwp 파싱 실패 또는 미지원 구조 감지 ({e}). LibreOffice 앙상블 엔진으로 자동 전환합니다.")

        # 2차 시도 (Fallback & Quality Ensemble): LibreOffice ➔ PDF ➔ PyMuPDF 구조화 파서
        try:
            temp_dir = path.parent / "temp_parsed_pdf"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # LibreOffice로 고화질 PDF 생성
            pdf_path = convert_hwp_to_pdf(str(path), output_dir=str(temp_dir))
            
            # PDF 고품질 파서로 본문 및 표 추출
            parsed_pdf = self.pdf_parser.parse(pdf_path)
            parsed_pdf["source_file"] = path.name
            parsed_pdf["file_type"] = path.suffix.lower().replace(".", "")
            parsed_pdf["engine_used"] = "libreoffice-pymupdf-ensemble"
            
            # 임시 PDF 정리
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass

            return parsed_pdf
        except Exception as e:
            raise RuntimeError(f"HWP 듀얼 엔진 파싱 모두 실패: {str(e)}")
