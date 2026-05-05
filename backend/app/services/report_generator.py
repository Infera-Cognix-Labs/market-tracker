from __future__ import annotations

from copy import copy
from io import BytesIO
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.models.api import WeeklyDigest


BRAND_NAVY = "17324D"
BRAND_BLUE = "2563EB"
INK = "111827"
MUTED = "6B7280"
SURFACE = "F8FAFC"
BORDER = "D9E2EC"
HEADER_FILL = "EAF1F8"
WARN_FILL = "FFF7ED"


def _value(value: Any) -> str:
    enum_value = getattr(value, "value", value)
    return "" if enum_value is None else str(enum_value)


def _join_values(values: list[Any] | None) -> str:
    return ", ".join(_value(value) for value in values or [])


def _safe_pdf_text(value: Any) -> str:
    text = _value(value)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _pdf_rgb(hex_color: str) -> tuple[int, int, int]:
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


class ReportPDFGenerator:
    def __init__(self, digest: "WeeklyDigest") -> None:
        self.digest = digest

    def generate(self) -> bytes:
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(14, 14, 14)
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.add_page()

        self._draw_header(pdf)
        self._draw_summary(pdf)
        self._draw_trackers(pdf)
        self._draw_threats(pdf)

        return bytes(pdf.output())

    def _set_text_color(self, pdf: FPDF, hex_color: str) -> None:
        pdf.set_text_color(*_pdf_rgb(hex_color))

    def _set_fill_color(self, pdf: FPDF, hex_color: str) -> None:
        pdf.set_fill_color(*_pdf_rgb(hex_color))

    def _section_title(self, pdf: FPDF, title: str) -> None:
        pdf.ln(5)
        self._set_text_color(pdf, BRAND_NAVY)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_text_color(pdf, INK)

    def _draw_header(self, pdf: FPDF) -> None:
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        self._set_fill_color(pdf, BRAND_NAVY)
        pdf.rect(pdf.l_margin, 12, page_width, 28, "F")

        pdf.set_xy(pdf.l_margin + 5, 17)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 17)
        pdf.cell(
            page_width - 10,
            8,
            "Weekly Digest Report",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(
            page_width - 10,
            6,
            _safe_pdf_text(f"{self.digest.week_start} to {self.digest.week_end}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        pdf.set_y(46)
        self._set_text_color(pdf, INK)
        self._set_fill_color(pdf, SURFACE)
        pdf.rect(pdf.l_margin, pdf.get_y(), page_width, 20, "F")
        pdf.set_draw_color(*_pdf_rgb(BORDER))
        pdf.rect(pdf.l_margin, pdf.get_y(), page_width, 20)

        meta = [
            ("Digest Code", self.digest.digest_code),
            ("Created", self.digest.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("Trackers", len(self.digest.tracker_refs)),
        ]
        col_width = page_width / 3
        y = pdf.get_y() + 4
        for index, (label, value) in enumerate(meta):
            x = pdf.l_margin + (index * col_width) + 5
            pdf.set_xy(x, y)
            self._set_text_color(pdf, MUTED)
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(
                col_width - 10,
                4,
                label.upper(),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_x(x)
            self._set_text_color(pdf, INK)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(col_width - 10, 5, _safe_pdf_text(value))
        pdf.set_y(72)

    def _draw_summary(self, pdf: FPDF) -> None:
        self._section_title(pdf, "Executive Summary")
        metrics = [
            ("New Entrants", self.digest.summary.new_entrant_count),
            ("Returning", self.digest.summary.returning_count),
            ("Top 10 Entry", self.digest.summary.top10_enter_count),
            ("Price Changes", self.digest.summary.price_change_count),
            ("Listing Changes", self.digest.summary.listing_change_count),
        ]
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        gap = 3
        card_width = (page_width - gap * (len(metrics) - 1)) / len(metrics)
        y = pdf.get_y()
        for index, (label, value) in enumerate(metrics):
            x = pdf.l_margin + index * (card_width + gap)
            self._set_fill_color(pdf, SURFACE)
            pdf.set_draw_color(*_pdf_rgb(BORDER))
            pdf.rect(x, y, card_width, 22, "DF")
            pdf.set_xy(x + 3, y + 4)
            self._set_text_color(pdf, BRAND_BLUE)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(
                card_width - 6,
                6,
                str(value),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
                align="C",
            )
            pdf.set_x(x + 3)
            self._set_text_color(pdf, MUTED)
            pdf.set_font("Helvetica", "B", 6.8)
            pdf.multi_cell(card_width - 6, 4, label.upper(), align="C")
        pdf.set_y(y + 25)

    def _draw_trackers(self, pdf: FPDF) -> None:
        self._section_title(pdf, "Trackers Included")
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        name_width = page_width * 0.68
        type_width = page_width - name_width
        self._table_header(pdf, [("Tracker Name", name_width), ("Type", type_width)])
        for ref in self.digest.tracker_refs:
            y = pdf.get_y()
            row_height = 8
            pdf.set_draw_color(*_pdf_rgb(BORDER))
            pdf.rect(pdf.l_margin, y, name_width, row_height)
            pdf.rect(pdf.l_margin + name_width, y, type_width, row_height)
            pdf.set_xy(pdf.l_margin + 2, y + 2)
            pdf.set_font("Helvetica", "", 8.5)
            self._set_text_color(pdf, INK)
            pdf.cell(name_width - 4, 4, _safe_pdf_text(ref.tracker_name))
            pdf.set_xy(pdf.l_margin + name_width + 2, y + 2)
            self._set_text_color(pdf, BRAND_NAVY)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(type_width - 4, 4, _safe_pdf_text(ref.tracker_type.value))
            pdf.set_y(y + row_height)

    def _draw_threats(self, pdf: FPDF) -> None:
        self._section_title(pdf, f"Threat Analysis ({len(self.digest.threats)})")
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        if not self.digest.threats:
            self._set_text_color(pdf, MUTED)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(
                0,
                7,
                "No threats detected during this period.",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            return

        for i, threat in enumerate(self.digest.threats, 1):
            min_height = 32
            if pdf.get_y() + min_height > pdf.page_break_trigger:
                pdf.add_page()
            y = pdf.get_y()
            self._set_fill_color(pdf, WARN_FILL if i == 1 else "FFFFFF")
            pdf.set_draw_color(*_pdf_rgb(BORDER))
            pdf.rect(pdf.l_margin, y, page_width, min_height, "DF")
            pdf.set_xy(pdf.l_margin + 4, y + 4)
            self._set_text_color(pdf, BRAND_NAVY)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(
                page_width - 8,
                5,
                _safe_pdf_text(f"{i}. {threat.asin} | {threat.marketplace}"),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_x(pdf.l_margin + 4)
            self._set_text_color(pdf, INK)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(page_width - 8, 5, _safe_pdf_text(f"Reason: {threat.reason}"))
            pdf.set_x(pdf.l_margin + 4)
            self._set_text_color(pdf, MUTED)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.multi_cell(
                page_width - 8,
                4.5,
                _safe_pdf_text(f"Event Types: {_join_values(threat.event_types)}"),
            )
            pdf.set_x(pdf.l_margin + 4)
            trackers = ", ".join(ref.tracker_name for ref in threat.tracker_refs)
            pdf.multi_cell(
                page_width - 8,
                4.5,
                _safe_pdf_text(f"Trackers: {trackers}"),
            )
            pdf.set_y(max(pdf.get_y() + 3, y + min_height + 3))

    def _table_header(self, pdf: FPDF, columns: list[tuple[str, float]]) -> None:
        y = pdf.get_y()
        x = pdf.l_margin
        self._set_fill_color(pdf, HEADER_FILL)
        pdf.set_draw_color(*_pdf_rgb(BORDER))
        pdf.set_font("Helvetica", "B", 8)
        self._set_text_color(pdf, BRAND_NAVY)
        for label, width in columns:
            pdf.rect(x, y, width, 7, "DF")
            pdf.set_xy(x + 2, y + 2)
            pdf.cell(width - 4, 3, label)
            x += width
        pdf.set_y(y + 7)


class ReportExcelGenerator:
    def __init__(self, digest: "WeeklyDigest") -> None:
        self.digest = digest

    def generate(self) -> bytes:
        wb = Workbook()
        wb.properties.title = "Weekly Digest Report"
        wb.properties.subject = self.digest.digest_code
        wb.properties.creator = "Market Tracker"

        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.sheet_properties.tabColor = BRAND_NAVY

        ws_summary["A1"] = "Weekly Digest Report"
        ws_summary["A1"].font = Font(bold=True, size=18, color="FFFFFF")
        ws_summary["A1"].fill = PatternFill("solid", fgColor=BRAND_NAVY)
        ws_summary["A1"].alignment = Alignment(vertical="center")
        ws_summary.merge_cells("A1:E1")
        ws_summary.row_dimensions[1].height = 28

        ws_summary["A3"] = "Week"
        ws_summary["B3"] = f"{self.digest.week_start} to {self.digest.week_end}"
        ws_summary["A4"] = "Code"
        ws_summary["B4"] = self.digest.digest_code
        ws_summary["A5"] = "Created"
        ws_summary["B5"] = self.digest.created_at.strftime("%Y-%m-%d %H:%M:%S")

        ws_summary["A7"] = "Metric"
        ws_summary["B7"] = "Count"
        self._style_header_row(ws_summary, 7, 1, 2)

        metrics = [
            ("New Entrants", self.digest.summary.new_entrant_count),
            ("Returning", self.digest.summary.returning_count),
            ("Top 10 Entry", self.digest.summary.top10_enter_count),
            ("Price Changes", self.digest.summary.price_change_count),
            ("Listing Changes", self.digest.summary.listing_change_count),
        ]
        for i, (label, value) in enumerate(metrics, start=8):
            ws_summary[f"A{i}"] = label
            ws_summary[f"B{i}"] = value
        self._style_summary_sheet(ws_summary)

        ws_trackers = wb.create_sheet("Trackers")
        ws_trackers.sheet_properties.tabColor = BRAND_BLUE
        ws_trackers["A1"] = "Tracker Name"
        ws_trackers["B1"] = "Type"
        self._style_header_row(ws_trackers, 1, 1, 2)
        for i, ref in enumerate(self.digest.tracker_refs, start=2):
            ws_trackers[f"A{i}"] = ref.tracker_name
            ws_trackers[f"B{i}"] = ref.tracker_type.value
        self._style_table_sheet(ws_trackers, widths={1: 42, 2: 18})

        ws_threats = wb.create_sheet("Threats")
        ws_threats.sheet_properties.tabColor = "DC2626"
        ws_threats["A1"] = "ASIN"
        ws_threats["B1"] = "Marketplace"
        ws_threats["C1"] = "Reason"
        ws_threats["D1"] = "Event Types"
        ws_threats["E1"] = "Trackers"
        self._style_header_row(ws_threats, 1, 1, 5)
        for i, threat in enumerate(self.digest.threats, start=2):
            ws_threats[f"A{i}"] = threat.asin
            ws_threats[f"B{i}"] = threat.marketplace
            ws_threats[f"C{i}"] = threat.reason
            ws_threats[f"D{i}"] = _join_values(threat.event_types)
            ws_threats[f"E{i}"] = ", ".join(ref.tracker_name for ref in threat.tracker_refs)
        self._style_table_sheet(
            ws_threats,
            widths={1: 16, 2: 16, 3: 58, 4: 52, 5: 46},
            wrap_columns={3, 4, 5},
        )

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _style_summary_sheet(self, ws: Worksheet) -> None:
        widths = {1: 22, 2: 30, 3: 16, 4: 16, 5: 16}
        for index, width in widths.items():
            ws.column_dimensions[get_column_letter(index)].width = width
        for row in range(3, 6):
            ws[f"A{row}"].font = Font(bold=True, color=MUTED)
            ws[f"B{row}"].font = Font(color=INK)
        for row in range(8, 13):
            ws[f"A{row}"].fill = PatternFill("solid", fgColor=SURFACE)
            ws[f"B{row}"].fill = PatternFill("solid", fgColor=SURFACE)
            ws[f"B{row}"].font = Font(bold=True, color=BRAND_BLUE)
            ws[f"B{row}"].alignment = Alignment(horizontal="right")
        self._apply_grid(ws, min_row=3, max_row=12, min_col=1, max_col=2)
        ws.freeze_panes = "A7"

    def _style_table_sheet(
        self,
        ws: Worksheet,
        *,
        widths: dict[int, int],
        wrap_columns: set[int] | None = None,
    ) -> None:
        wrap_columns = wrap_columns or set()
        for index, width in widths.items():
            ws.column_dimensions[get_column_letter(index)].width = width
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        self._apply_grid(
            ws,
            min_row=1,
            max_row=ws.max_row,
            min_col=1,
            max_col=ws.max_column,
        )
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=cell.column in wrap_columns,
                )

    def _style_header_row(
        self, ws: Worksheet, row: int, min_col: int, max_col: int
    ) -> None:
        for column in range(min_col, max_col + 1):
            cell = ws.cell(row=row, column=column)
            cell.font = Font(bold=True, color=BRAND_NAVY)
            cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
            cell.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 22

    def _apply_grid(
        self,
        ws: Worksheet,
        *,
        min_row: int,
        max_row: int,
        min_col: int,
        max_col: int,
    ) -> None:
        thin = Side(style="thin", color=BORDER)
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for row in ws.iter_rows(
            min_row=min_row,
            max_row=max_row,
            min_col=min_col,
            max_col=max_col,
        ):
            for cell in row:
                cell.border = border
                alignment = copy(cell.alignment)
                alignment.vertical = "top"
                cell.alignment = alignment
