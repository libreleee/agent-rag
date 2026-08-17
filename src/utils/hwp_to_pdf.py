"""
한글 (HWP / HWPX) 및 오피스 문서 ➔ PDF 고품질 변환 모듈
1차 우선: rhwp-python (Rust 기반 네이티브 초고속 PDF 렌더러)
2차 폴백: LibreOffice Headless (기타 오피스 문서 및 앙상블)
"""
import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_hwp_to_pdf(input_path: str, output_dir: str | None = None) -> Path:
    """Convert a Hangul (.hwp, .hwpx) or Office file to PDF.

    Uses rhwp-python Rust engine as the primary converter for .hwp/.hwpx,
    and falls back to LibreOffice headless engine if needed.

    Args:
        input_path: Path to the source file (.hwp, .hwpx, .doc, .docx).
        output_dir: Destination directory. If None, saves in the same directory as input.

    Returns:
        Path to the successfully generated PDF file.
    """
    src_path = Path(input_path)
    if not src_path.is_file():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {src_path}")

    # Resolve output directory
    if output_dir is None:
        target_dir = src_path.parent
    else:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = target_dir / (src_path.stem + ".pdf")
    ext = src_path.suffix.lower()

    # 1. 1차 시도: HWP / HWPX인 경우 rhwp-python Rust 네이티브 PDF 내보내기
    if ext in [".hwp", ".hwpx"]:
        try:
            import rhwp
            doc = rhwp.parse(str(src_path))
            doc.export_pdf(str(pdf_path))
            
            if pdf_path.is_file() and pdf_path.stat().st_size > 0:
                logger.info(f"[rhwp] PDF 변환 성공: {pdf_path.name}")
                return pdf_path
        except Exception as e:
            logger.warning(f"rhwp PDF 변환 시도 중 경고 ({e}). LibreOffice 엔진으로 폴백합니다.")

    # 2. 2차 시도 (폴백 또는 기타 오피스 문서): LibreOffice Headless
    candidates = [
        os.getenv("LIBREOFFICE_PATH", ""),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    soffice_path = None
    for cand in candidates:
        if cand and Path(cand).is_file():
            soffice_path = Path(cand)
            break

    if not soffice_path:
        # If LibreOffice is also missing and rhwp already failed
        if pdf_path.is_file() and pdf_path.stat().st_size > 0:
            return pdf_path
        raise RuntimeError(
            "PDF 변환 실패: rhwp 및 LibreOffice 엔진 모두 실행할 수 없습니다."
        )

    cmd = [
        str(soffice_path),
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(target_dir),
        str(src_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if pdf_path.is_file() and pdf_path.stat().st_size > 0:
        return pdf_path

    # Check if LibreOffice generated with a sanitized filename
    possible_pdfs = list(target_dir.glob(f"*{src_path.stem}*.pdf"))
    if possible_pdfs:
        return possible_pdfs[0]

    raise RuntimeError(
        f"PDF 변환 실패: 파일이 생성되지 않았습니다.\nCommand stderr: {result.stderr}"
    )
