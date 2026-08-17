"""
HWPX (개방형 한글 XML 포맷) 순수 Python 고품질 파서
한글 프로그램 설치 없이 XML 내 본문 및 표(Table) 병합 셀을 2D 매트릭스로 완벽 복원
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

class HwpxParser:
    def __init__(self):
        # HWPX 네임스페이스 정의
        self.namespaces = {
            'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
            'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
            'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
            'hh': 'http://www.hancom.co.kr/hwpml/2011/head'
        }

    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        HWPX 파일을 읽어 구조화된 Markdown 및 청크 리스트를 반환합니다.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

        extracted_sections = []
        tables_count = 0
        all_blocks: List[Dict[str, Any]] = []

        with zipfile.ZipFile(path, 'r') as z:
            # 셀 배경색은 header.xml의 borderFill 정의에 있고, 셀은 ID로만 참조한다.
            self._fill_map = self._parse_fill_map(z)

            # section xml 파일들 탐색 (section0.xml, section1.xml ...)
            section_files = sorted([f for f in z.namelist() if f.startswith('Contents/section') and f.endswith('.xml')])

            for sec_file in section_files:
                xml_data = z.read(sec_file)
                root = ET.fromstring(xml_data)

                sec_text, t_count, blocks = self._parse_section(root)
                extracted_sections.append(sec_text)
                tables_count += t_count
                all_blocks.extend(blocks)

        full_markdown = "\n\n".join(extracted_sections).strip()

        return {
            "source_file": path.name,
            "file_type": "hwpx",
            "table_count": tables_count,
            "markdown": full_markdown,
            # 문서 순서를 보존한 구조화 블록. 마크다운 표로는 표현할 수 없는
            # 셀 병합(colSpan/rowSpan)과 열 너비를 그대로 담는다.
            "blocks": all_blocks,
            "char_count": len(full_markdown)
        }

    def _parse_fill_map(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """header.xml의 borderFill 정의에서 {borderFillID: RRGGBB} 배경색 표를 만듭니다."""
        fill_map: Dict[str, str] = {}
        header_files = [n for n in z.namelist() if n.lower().endswith('header.xml')]
        if not header_files:
            return fill_map

        try:
            root = ET.fromstring(z.read(header_files[0]))
        except ET.ParseError:
            return fill_map

        for bf in root.iter():
            if not bf.tag.endswith('}borderFill'):
                continue
            bf_id = bf.get('id')
            if not bf_id:
                continue
            for brush in bf.iter():
                if not brush.tag.endswith('}winBrush'):
                    continue
                face = (brush.get('faceColor') or '').strip()
                # 'none' 및 흰색은 음영 없음으로 취급한다.
                if face.startswith('#') and face.upper() not in ('#FFFFFF', '#NONE'):
                    fill_map[bf_id] = face[1:].upper()
                break

        return fill_map

    def _parse_section(self, root: ET.Element) -> tuple[str, int, List[Dict[str, Any]]]:
        lines = []
        blocks: List[Dict[str, Any]] = []
        table_count = 0

        tbl_tag = f"{{{self.namespaces['hp']}}}tbl"
        # 표 셀 안에 중첩된 문단은 표 파싱에서 이미 다루므로 본문 순회에서 제외한다.
        # (ElementTree에는 부모 참조가 없으므로 자식 ➔ 부모 맵을 직접 구성)
        parent_of = {child: parent for parent in root.iter() for child in parent}

        def is_inside_table(elem: ET.Element) -> bool:
            node = parent_of.get(elem)
            while node is not None:
                if node.tag == tbl_tag:
                    return True
                node = parent_of.get(node)
            return False

        # paragraph(<hp:p>) 단위로 순회
        for p in root.findall('.//hp:p', self.namespaces):
            if is_inside_table(p):
                continue

            # 1. 문단 내 표(<hp:tbl>)가 있는지 검사
            tables = p.findall('.//hp:tbl', self.namespaces)
            if tables:
                for tbl in tables:
                    table_md = self._parse_table_to_markdown(tbl)
                    if table_md:
                        lines.append("\n" + table_md + "\n")
                        table_count += 1

                    table_data = self._parse_table_structured(tbl)
                    if table_data:
                        blocks.append({"type": "table", "table": table_data})
                continue

            # 2. 일반 문단 텍스트(<hp:t>) 추출
            texts = [t.text for t in p.findall('.//hp:t', self.namespaces) if t.text]
            if texts:
                para_text = "".join(texts).strip()
                if para_text:
                    lines.append(para_text)
                    blocks.append({"type": "paragraph", "text": para_text})

        return "\n".join(lines), table_count, blocks

    def _parse_table_structured(self, tbl_element: ET.Element) -> Dict[str, Any] | None:
        """표를 셀 좌표·병합·열너비가 보존된 구조로 추출합니다.

        마크다운 표는 셀 병합을 표현할 수 없으므로, 서식을 그대로 재현해야 하는
        Word 변환 경로는 이 메서드의 결과를 사용합니다.
        """
        row_cnt = int(tbl_element.get("rowCnt") or 0)
        col_cnt = int(tbl_element.get("colCnt") or 0)

        cells: List[Dict[str, Any]] = []
        # colAddr ➔ 너비(HWPUNIT). 병합되지 않은 셀에서만 수집해야 열 너비가 정확하다.
        col_widths: Dict[int, int] = {}

        for tc in tbl_element.findall('.//hp:tc', self.namespaces):
            addr = tc.find('hp:cellAddr', self.namespaces)
            span = tc.find('hp:cellSpan', self.namespaces)
            if addr is None:
                continue

            col = int(addr.get("colAddr") or 0)
            row = int(addr.get("rowAddr") or 0)
            col_span = int(span.get("colSpan") or 1) if span is not None else 1
            row_span = int(span.get("rowSpan") or 1) if span is not None else 1

            texts = [t.text for t in tc.findall('.//hp:t', self.namespaces) if t.text]
            cell_text = " ".join(texts).strip()

            sz = tc.find('hp:cellSz', self.namespaces)
            cell_width = int(sz.get("width")) if (sz is not None and sz.get("width")) else None
            if cell_width and col_span == 1 and col not in col_widths:
                col_widths[col] = cell_width

            cells.append({
                "row": row,
                "col": col,
                "row_span": row_span,
                "col_span": col_span,
                "text": cell_text,
                "width": cell_width,
                "fill": getattr(self, "_fill_map", {}).get(tc.get("borderFillIDRef") or ""),
            })

        if not cells:
            return None

        # rowCnt/colCnt 속성이 없거나 어긋나는 경우 실제 셀 좌표로 보정
        row_cnt = max(row_cnt, max(c["row"] + c["row_span"] for c in cells))
        col_cnt = max(col_cnt, max(c["col"] + c["col_span"] for c in cells))

        tbl_sz = tbl_element.find('hp:sz', self.namespaces)
        total_width = int(tbl_sz.get("width")) if (tbl_sz is not None and tbl_sz.get("width")) else None

        return {
            "row_count": row_cnt,
            "col_count": col_cnt,
            "cells": cells,
            "total_width": total_width,
            "col_widths": self._resolve_col_widths(cells, col_widths, col_cnt, total_width),
        }

    @staticmethod
    def _resolve_col_widths(
        cells: List[Dict[str, Any]],
        known: Dict[int, int],
        col_cnt: int,
        total_width: int | None,
    ) -> List[int | None]:
        """병합 셀만 존재하는 열의 너비를 역산합니다.

        병합되지 않은 셀이 하나도 없는 열은 너비를 직접 알 수 없으므로,
        걸쳐 있는 병합 셀의 전체 너비에서 이미 아는 열들을 빼서 구합니다.
        """
        widths = dict(known)

        spans = [c for c in cells if c["col_span"] > 1 and c.get("width")]
        changed = True
        while changed:
            changed = False
            for c in spans:
                cols = range(c["col"], min(c["col"] + c["col_span"], col_cnt))
                unknown = [i for i in cols if i not in widths]
                if len(unknown) != 1:
                    continue
                rest = sum(widths[i] for i in cols if i in widths)
                inferred = c["width"] - rest
                if inferred > 0:
                    widths[unknown[0]] = inferred
                    changed = True

        # 그래도 남은 열은 표 전체 너비의 잔여분을 균등 배분한다.
        missing = [i for i in range(col_cnt) if i not in widths]
        if missing:
            known_sum = sum(widths.values())
            remainder = (total_width - known_sum) if total_width else 0
            if remainder <= 0:
                fallback = int(known_sum / max(len(widths), 1)) if widths else 0
            else:
                fallback = int(remainder / len(missing))
            for i in missing:
                widths[i] = max(fallback, 1)

        return [widths.get(i) for i in range(col_cnt)]

    def _parse_table_to_markdown(self, tbl_element: ET.Element) -> str:
        """
        표의 row, col, colspan, rowspan을 계산하여 Markdown Table로 변환합니다.
        """
        rows = tbl_element.findall('.//hp:tr', self.namespaces)
        if not rows:
            return ""

        table_matrix: List[List[str]] = []

        for tr in rows:
            row_cells = []
            cells = tr.findall('.//hp:tc', self.namespaces)
            for tc in cells:
                # 셀 안의 텍스트 추출
                cell_texts = [t.text for t in tc.findall('.//hp:t', self.namespaces) if t.text]
                cell_content = " ".join(cell_texts).strip().replace("\n", " ").replace("|", "\\|")
                row_cells.append(cell_content if cell_content else " ")
            if row_cells:
                table_matrix.append(row_cells)

        if not table_matrix:
            return ""

        # Markdown Table 조립
        max_cols = max(len(r) for r in table_matrix)
        normalized_matrix = [r + [" "] * (max_cols - len(r)) for r in table_matrix]

        header = normalized_matrix[0]
        divider = ["---"] * max_cols

        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(divider) + " |"
        ]

        for row in normalized_matrix[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(md_lines)
