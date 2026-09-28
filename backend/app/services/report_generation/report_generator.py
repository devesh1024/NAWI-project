"""
NAWI Test Report generator.

Consumes the `data` dictionary exactly as returned by the
`/api/test-sessions/{id}/report-data` endpoint and produces a
formatted, print-ready DOCX laboratory test report.
"""

from datetime import datetime

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Emu

from .sample_report_data import sample_report_data


# ---------------------------------------------------------------------------
# Layout / style constants
# ---------------------------------------------------------------------------

FONT_NAME = "Calibri"
BODY_SIZE = Pt(10)

PAGE_MARGIN = Inches(0.8)
PAGE_WIDTH = Inches(8.27)
USABLE_WIDTH = PAGE_WIDTH - (PAGE_MARGIN * 2)

ACCENT_HEX = "2F5496"
LABEL_SHADE_HEX = "EDF1F7"
BORDER_HEX = "A6ACB4"

PASS_COLOR = RGBColor(0x1E, 0x7B, 0x34)
FAIL_COLOR = RGBColor(0xC0, 0x00, 0x00)
NEUTRAL_COLOR = RGBColor(0x22, 0x22, 0x22)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


# ---------------------------------------------------------------------------
# Low-level XML helpers
# ---------------------------------------------------------------------------

def _set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()

    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)

    tcPr.append(shd)


def _set_cell_borders(cell, hex_color=BORDER_HEX, size=4):
    tcPr = cell._tc.get_or_add_tcPr()

    borders = OxmlElement("w:tcBorders")

    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), hex_color)

        borders.append(el)

    tcPr.append(borders)


def _set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()

    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")

    trPr.append(header)


def _prevent_row_split(row):
    trPr = row._tr.get_or_add_trPr()

    cant_split = OxmlElement("w:cantSplit")

    trPr.append(cant_split)


def _set_fixed_layout(table):
    tblPr = table._tbl.tblPr

    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")

    tblPr.append(layout)


def _set_column_widths(table, widths):
    """Apply explicit widths to the table grid and every cell."""

    widths = [Emu(int(w)) for w in widths]

    table.autofit = False

    _set_fixed_layout(table)

    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width

    for idx, width in enumerate(widths):
        table.columns[idx].width = width


def _add_field(run_container, label, value, bold_label=True):
    p = run_container.add_paragraph()

    label_run = p.add_run(f"{label}: ")

    label_run.bold = bold_label
    label_run.font.name = FONT_NAME
    label_run.font.size = BODY_SIZE

    value_run = p.add_run(
        "" if value is None else str(value)
    )

    value_run.font.name = FONT_NAME
    value_run.font.size = BODY_SIZE

    return p


def _set_cell_text(
    cell,
    text,
    bold=False,
    color=None,
    size=BODY_SIZE,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    vcenter=True
):
    cell.text = ""

    p = cell.paragraphs[0]
    p.alignment = align

    run = p.add_run(
        "" if text is None else str(text)
    )

    run.bold = bold
    run.font.name = FONT_NAME
    run.font.size = size

    if color is not None:
        run.font.color.rgb = color

    if vcenter:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    return run


def _status_color(value):
    v = str(value).strip().upper() if value else ""

    if v == "PASS":
        return PASS_COLOR

    if v == "FAIL":
        return FAIL_COLOR

    return NEUTRAL_COLOR


def _add_page_number_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]

    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.text = ""

    run = p.add_run("Page ")

    run.font.name = FONT_NAME
    run.font.size = Pt(8.5)

    def _field(paragraph, code, run_font_setup):
        r = paragraph.add_run()
        run_font_setup(r)

        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(
            qn("w:fldCharType"),
            "begin"
        )

        instr = OxmlElement("w:instrText")
        instr.set(
            qn("xml:space"),
            "preserve"
        )
        instr.text = code

        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(
            qn("w:fldCharType"),
            "separate"
        )

        fld_end = OxmlElement("w:fldChar")
        fld_end.set(
            qn("w:fldCharType"),
            "end"
        )

        r._r.append(fld_begin)

        r2 = paragraph.add_run()
        run_font_setup(r2)
        r2._r.append(instr)

        r3 = paragraph.add_run()
        run_font_setup(r3)
        r3._r.append(fld_sep)

        r4 = paragraph.add_run()
        run_font_setup(r4)
        r4._r.append(fld_end)

    def _setup(r):
        r.font.name = FONT_NAME
        r.font.size = Pt(8.5)

    _field(
        p,
        "PAGE",
        _setup
    )

    mid = p.add_run(" of ")

    mid.font.name = FONT_NAME
    mid.font.size = Pt(8.5)

    _field(
        p,
        "NUMPAGES",
        _setup
    )


def _add_header(section, laboratory_name, session_number):
    header = section.header
    p = header.paragraphs[0]
    p.text = ""

    left = p.add_run(
        f"{laboratory_name} — NAWI Test Report"
    )

    left.font.name = FONT_NAME
    left.font.size = Pt(8.5)
    left.font.color.rgb = RGBColor(
        0x55,
        0x55,
        0x55
    )

    p.add_run("\t\t")

    right = p.add_run(
        f"Session: {session_number}"
    )

    right.font.name = FONT_NAME
    right.font.size = Pt(8.5)
    right.font.color.rgb = RGBColor(
        0x55,
        0x55,
        0x55
    )

    pPr = p._p.get_or_add_pPr()

    tabs = OxmlElement("w:tabs")

    tab_el = OxmlElement("w:tab")
    tab_el.set(
        qn("w:val"),
        "right"
    )
    tab_el.set(
        qn("w:pos"),
        str(int(USABLE_WIDTH))
    )

    tabs.append(tab_el)
    pPr.append(tabs)

    pBdr = OxmlElement("w:pBdr")

    bottom = OxmlElement("w:bottom")
    bottom.set(
        qn("w:val"),
        "single"
    )
    bottom.set(
        qn("w:sz"),
        "6"
    )
    bottom.set(
        qn("w:space"),
        "4"
    )
    bottom.set(
        qn("w:color"),
        BORDER_HEX
    )

    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_horizontal_rule(
    document,
    color=ACCENT_HEX,
    size=18
):
    p = document.add_paragraph()

    p.paragraph_format.space_after = Pt(10)

    pPr = p._p.get_or_add_pPr()

    pBdr = OxmlElement("w:pBdr")

    bottom = OxmlElement("w:bottom")
    bottom.set(
        qn("w:val"),
        "single"
    )
    bottom.set(
        qn("w:sz"),
        str(size)
    )
    bottom.set(
        qn("w:space"),
        "1"
    )
    bottom.set(
        qn("w:color"),
        color
    )

    pBdr.append(bottom)
    pPr.append(pBdr)


def _style_heading(
    paragraph,
    keep_with_next=True
):
    paragraph.paragraph_format.keep_with_next = (
        keep_with_next
    )

    for run in paragraph.runs:
        run.font.name = FONT_NAME


def _apply_base_styles(document):
    normal = document.styles["Normal"]

    normal.font.name = FONT_NAME
    normal.font.size = BODY_SIZE
    normal.font.color.rgb = NEUTRAL_COLOR

    normal.paragraph_format.space_after = Pt(4)

    for level, size, color in (
        ("Title", 22, ACCENT_HEX),
        ("Heading 1", 13, ACCENT_HEX),
        ("Heading 2", 11.5, "1A1A1A"),
        ("Heading 3", 10.5, "1A1A1A"),
    ):
        style = document.styles[level]

        style.font.name = FONT_NAME
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(
            color
        )
        style.font.bold = True

        style.paragraph_format.space_before = (
            Pt(10)
            if level != "Title"
            else Pt(0)
        )

        style.paragraph_format.space_after = Pt(6)


# ---------------------------------------------------------------------------
# Reusable table builders
# ---------------------------------------------------------------------------

def _add_kv_table(
    document,
    pairs,
    label_width=Inches(2.1),
    header=None
):
    """A two-column label/value table."""

    rows = len(pairs) + (
        1 if header else 0
    )

    table = document.add_table(
        rows=rows,
        cols=2
    )

    table.alignment = 1

    value_width = (
        USABLE_WIDTH - label_width
    )

    r = 0

    if header:
        _set_cell_text(
            table.rows[0].cells[0],
            header[0],
            bold=True,
            color=WHITE
        )

        _set_cell_text(
            table.rows[0].cells[1],
            header[1],
            bold=True,
            color=WHITE
        )

        for cell in table.rows[0].cells:
            _set_cell_background(
                cell,
                ACCENT_HEX
            )
            _set_cell_borders(cell)

        _set_repeat_header(
            table.rows[0]
        )

        r = 1

    for label, value in pairs:
        row = table.rows[r]

        _set_cell_text(
            row.cells[0],
            label,
            bold=True
        )

        _set_cell_background(
            row.cells[0],
            LABEL_SHADE_HEX
        )

        _set_cell_text(
            row.cells[1],
            value
        )

        for cell in row.cells:
            _set_cell_borders(cell)

        _prevent_row_split(row)

        r += 1

    _set_column_widths(
        table,
        [
            label_width,
            value_width
        ]
    )

    document.add_paragraph().paragraph_format.space_after = Pt(2)

    return table


def _add_columnar_table(
    document,
    headers,
    col_widths,
    rows_data,
    align_cols=None
):
    """A standard header-row table."""

    table = document.add_table(
        rows=1,
        cols=len(headers)
    )

    table.alignment = 1

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]

        _set_cell_text(
            cell,
            h,
            bold=True,
            color=WHITE,
            align=WD_ALIGN_PARAGRAPH.CENTER
        )

        _set_cell_background(
            cell,
            ACCENT_HEX
        )

        _set_cell_borders(cell)

    _set_repeat_header(
        table.rows[0]
    )

    for row_values in rows_data:
        row = table.add_row()

        for i, val in enumerate(row_values):
            align = (
                align_cols[i]
                if align_cols
                else WD_ALIGN_PARAGRAPH.LEFT
            )

            color = None
            bold = False

            if isinstance(val, tuple):
                text, color, bold = val
            else:
                text = val

            _set_cell_text(
                row.cells[i],
                text,
                align=align,
                color=color,
                bold=bold
            )

            _set_cell_borders(
                row.cells[i]
            )

        _prevent_row_split(row)

    _set_column_widths(
        table,
        col_widths
    )

    document.add_paragraph().paragraph_format.space_after = Pt(2)

    return table


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_masthead(document, data):
    laboratory = data["laboratory"]
    standard = data["standard"]

    title = document.add_heading(
        "NAWI TEST REPORT",
        level=0
    )

    title.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    _style_heading(title)

    subtitle = document.add_paragraph()

    subtitle.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = subtitle.add_run(
        "Non-Automatic Weighing Instrument — Test Certificate"
    )

    run.font.name = FONT_NAME
    run.font.size = Pt(10.5)
    run.font.color.rgb = RGBColor(
        0x55,
        0x55,
        0x55
    )
    run.italic = True

    subtitle.paragraph_format.space_after = Pt(8)

    _add_horizontal_rule(document)

    table = document.add_table(
        rows=1,
        cols=2
    )

    table.alignment = 1

    left_cell, right_cell = (
        table.rows[0].cells
    )

    left_cell.paragraphs[0].text = ""

    _add_field(
        left_cell,
        "Laboratory",
        laboratory["name"]
    )

    _add_field(
        left_cell,
        "Address",
        f"{laboratory['address']}, "
        f"{laboratory['city']}, "
        f"{laboratory['state']} - "
        f"{laboratory['pincode']}, "
        f"{laboratory['country']}"
    )

    _add_field(
        left_cell,
        "Registration No.",
        laboratory["registration_number"]
    )

    _add_field(
        left_cell,
        "Phone",
        laboratory["phone"]
    )

    _add_field(
        left_cell,
        "Email",
        laboratory["email"]
    )

    right_cell.paragraphs[0].text = ""

    report_info = data.get("report") or {}

    _add_field(
        right_cell,
        "Report No.",
        report_info.get(
            "report_number",
            "[REPORT NUMBER PLACEHOLDER]"
        )
    )

    _add_field(
        right_cell,
        "Report Date",
        report_info.get(
            "report_date",
            "[REPORT DATE PLACEHOLDER]"
        )
    )

    _add_field(
        right_cell,
        "Standard",
        f"{standard['standard_code']} — "
        f"{standard['title']}"
    )

    _add_field(
        right_cell,
        "Edition / Version",
        f"{standard['version']} "
        f"({standard['edition_year']})"
    )

    for cell in (
        left_cell,
        right_cell
    ):
        _set_cell_borders(cell)

        cell.vertical_alignment = (
            WD_ALIGN_VERTICAL.TOP
        )

    _set_column_widths(
        table,
        [
            USABLE_WIDTH / 2,
            USABLE_WIDTH / 2
        ]
    )

    document.add_paragraph().paragraph_format.space_after = Pt(4)


def _build_session_section(document, data):
    heading = document.add_heading(
        "1. Test Session Information",
        level=1
    )

    _style_heading(heading)

    session = data["test_session"]
    result = session["overall_result"]

    table = document.add_table(
        rows=4,
        cols=2
    )

    pairs = [
        (
            "Session Number",
            session["session_number"]
        ),
        (
            "Application Number",
            session["application_number"]
        ),
        (
            "Test Type",
            session["test_type"]
        ),
    ]

    label_width = Inches(2.1)

    for i, (label, value) in enumerate(pairs):
        row = table.rows[i]

        _set_cell_text(
            row.cells[0],
            label,
            bold=True
        )

        _set_cell_background(
            row.cells[0],
            LABEL_SHADE_HEX
        )

        _set_cell_text(
            row.cells[1],
            value
        )

        for c in row.cells:
            _set_cell_borders(c)

        _prevent_row_split(row)

    row = table.rows[3]

    _set_cell_text(
        row.cells[0],
        "Overall Result",
        bold=True
    )

    _set_cell_background(
        row.cells[0],
        LABEL_SHADE_HEX
    )

    _set_cell_text(
        row.cells[1],
        result,
        bold=True,
        color=_status_color(result)
    )

    for c in row.cells:
        _set_cell_borders(c)

    _prevent_row_split(row)

    _set_column_widths(
        table,
        [
            label_width,
            USABLE_WIDTH - label_width
        ]
    )

    document.add_paragraph().paragraph_format.space_after = Pt(2)


def _build_instrument_section(document, data):
    heading = document.add_heading(
        "2. Instrument Under Test",
        level=1
    )

    _style_heading(heading)

    instrument = data["instrument"]

    pairs = [
        (
            "Manufacturer",
            instrument["manufacturer"]
        ),
        (
            "Model",
            instrument["model"]
        ),
        (
            "Type Designation",
            instrument["type_designation"]
        ),
        (
            "Serial Number",
            instrument["serial_number"]
        ),
        (
            "Instrument Type",
            instrument["instrument_type"]
        ),
        (
            "Category",
            instrument["category"]
        ),
        (
            "Accuracy Class",
            instrument["accuracy_class"]
        ),
        (
            "Minimum Capacity (Min)",
            f"{instrument['min_capacity']} "
            f"{instrument['unit']}"
        ),
        (
            "Maximum Capacity (Max)",
            f"{instrument['max_capacity']} "
            f"{instrument['unit']}"
        ),
        (
            "Scale Interval (d)",
            f"{instrument['scale_interval']} "
            f"{instrument['unit']}"
        ),
        (
            "Verification Scale Interval (e)",
            f"{instrument['verification_scale_interval']} "
            f"{instrument['unit']}"
        ),
        (
            "Number of Intervals",
            instrument["number_of_intervals"]
        ),
        (
            "Unit",
            instrument["unit"]
        ),
    ]

    _add_kv_table(
        document,
        pairs,
        label_width=Inches(2.6),
        header=(
            "Specification",
            "Value"
        )
    )


def _build_tester_section(document, data):
    heading = document.add_heading(
        "3. Tester Information",
        level=1
    )

    _style_heading(heading)

    tester = data["tester"]

    full_name = " ".join(
        part
        for part in [
            tester.get("first_name"),
            tester.get("last_name")
        ]
        if part
    )

    pairs = [
        (
            "Name",
            full_name
        ),
        (
            "Designation",
            tester.get("designation")
        ),
    ]

    _add_kv_table(
        document,
        pairs,
        label_width=Inches(2.1)
    )


def _build_test_block(
    document,
    test,
    index
):
    test_name = (
        test.get("test_name")
        or test.get("test_code")
        or "Unnamed Test"
    )

    heading = document.add_heading(
        f"Test {index} — {test_name}",
        level=2
    )

    _style_heading(heading)

    if test["applicability_status"] != "APPLICABLE":
        p = document.add_paragraph()

        run = p.add_run(
            "Applicability: Not Applicable"
        )

        run.bold = True
        run.font.name = FONT_NAME
        run.font.color.rgb = NEUTRAL_COLOR

        if test.get("na_reason"):
            reason_p = document.add_paragraph()

            reason_run = reason_p.add_run(
                f"Reason: {test['na_reason']}"
            )

            reason_run.italic = True
            reason_run.font.name = FONT_NAME

        document.add_paragraph().paragraph_format.space_after = Pt(2)

        return

    # -----------------------------------------------------------------------
    # Observations
    # -----------------------------------------------------------------------

    obs_heading = document.add_heading(
        "Observations",
        level=3
    )

    _style_heading(obs_heading)

    observations = (
        test.get("observations") or []
    )

    if not observations:
        document.add_paragraph(
            "No observation data recorded for this test."
        )

    else:
        rows = []

        for obs in observations:
            value = (
                obs["value_numeric"]
                if obs["value_numeric"] is not None
                else obs["value_text"]
            )

            rows.append(
                [
                    obs["parameter_name"],
                    value,
                    obs["unit"] or "—"
                ]
            )

        _add_columnar_table(
            document,
            headers=[
                "Parameter",
                "Value",
                "Unit"
            ],
            col_widths=[
                USABLE_WIDTH * 0.5,
                USABLE_WIDTH * 0.25,
                USABLE_WIDTH * 0.25
            ],
            rows_data=rows,
            align_cols=[
                WD_ALIGN_PARAGRAPH.LEFT,
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER
            ],
        )

    # -----------------------------------------------------------------------
    # Calculations
    # -----------------------------------------------------------------------

    calc_heading = document.add_heading(
        "Calculations",
        level=3
    )

    _style_heading(calc_heading)

    calculations = (
        test.get("calculations") or []
    )

    if not calculations:
        document.add_paragraph(
            "No calculation data recorded for this test."
        )

    else:
        rows = []

        for calc in calculations:
            rows.append(
                [
                    calc["calculation_type"],
                    calc["calculated_value"],
                    calc["unit"] or "—",
                    calc["formula"] or "—",
                ]
            )

        _add_columnar_table(
            document,
            headers=[
                "Calculation",
                "Calculated Value",
                "Unit",
                "Formula"
            ],
            col_widths=[
                USABLE_WIDTH * 0.26,
                USABLE_WIDTH * 0.18,
                USABLE_WIDTH * 0.14,
                USABLE_WIDTH * 0.42
            ],
            rows_data=rows,
            align_cols=[
                WD_ALIGN_PARAGRAPH.LEFT,
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.LEFT
            ],
        )

    # -----------------------------------------------------------------------
    # Results
    # -----------------------------------------------------------------------

    res_heading = document.add_heading(
        "Result",
        level=3
    )

    _style_heading(res_heading)

    results = (
        test.get("results") or []
    )

    if not results:
        document.add_paragraph(
            "No result data recorded for this test."
        )

    else:
        field_labels = [
            "Measured Value",
            "MPE",
            "Error",
            "Corrected Error",
            "Acceptance Condition",
            "Result",
        ]

        n = len(results)

        label_col_width = Inches(1.9)

        data_col_width = (
            USABLE_WIDTH - label_col_width
        ) / n

        table = document.add_table(
            rows=1 + len(field_labels),
            cols=1 + n
        )

        table.alignment = 1

        header_row = table.rows[0]

        _set_cell_text(
            header_row.cells[0],
            "Field",
            bold=True,
            color=WHITE
        )

        _set_cell_background(
            header_row.cells[0],
            ACCENT_HEX
        )

        for i in range(n):
            label = (
                "Value"
                if n == 1
                else f"Reading {i + 1}"
            )

            _set_cell_text(
                header_row.cells[i + 1],
                label,
                bold=True,
                color=WHITE,
                align=WD_ALIGN_PARAGRAPH.CENTER
            )

            _set_cell_background(
                header_row.cells[i + 1],
                ACCENT_HEX
            )

        for c in header_row.cells:
            _set_cell_borders(c)

        _set_repeat_header(header_row)

        field_keys = [
            "measured_value",
            "mpe_value",
            "error_value",
            "corrected_error",
            "acceptance_condition",
            "pass_fail",
        ]

        for r_idx, (
            label,
            key
        ) in enumerate(
            zip(
                field_labels,
                field_keys
            )
        ):
            row = table.rows[
                r_idx + 1
            ]

            _set_cell_text(
                row.cells[0],
                label,
                bold=True
            )

            _set_cell_background(
                row.cells[0],
                LABEL_SHADE_HEX
            )

            for c_idx, result in enumerate(results):
                value = result.get(key)

                if key == "pass_fail":
                    _set_cell_text(
                        row.cells[c_idx + 1],
                        value,
                        bold=True,
                        color=_status_color(value),
                        align=WD_ALIGN_PARAGRAPH.CENTER
                    )
                else:
                    _set_cell_text(
                        row.cells[c_idx + 1],
                        value,
                        align=WD_ALIGN_PARAGRAPH.CENTER
                    )

            for c in row.cells:
                _set_cell_borders(c)

            _prevent_row_split(row)

        widths = (
            [label_col_width]
            + [data_col_width] * n
        )

        _set_column_widths(
            table,
            widths
        )

        document.add_paragraph().paragraph_format.space_after = Pt(2)

        for i, result in enumerate(results):
            summary = result.get(
                "result_summary"
            )

            if summary:
                p = document.add_paragraph()

                prefix = (
                    "Summary: "
                    if n == 1
                    else f"Reading {i + 1} summary: "
                )

                run = p.add_run(prefix)

                run.bold = True
                run.italic = True
                run.font.name = FONT_NAME
                run.font.size = Pt(9.5)

                run2 = p.add_run(summary)

                run2.italic = True
                run2.font.name = FONT_NAME
                run2.font.size = Pt(9.5)

    document.add_paragraph().paragraph_format.space_after = Pt(6)


def _build_results_section(document, data):
    heading = document.add_heading(
        "4. Test Results",
        level=1
    )

    _style_heading(heading)

    for index, test in enumerate(
        data["tests"],
        start=1
    ):
        _build_test_block(
            document,
            test,
            index
        )


def _build_conclusion_section(
    document,
    data
):
    heading = document.add_heading(
        "5. Overall Conclusion",
        level=1
    )

    _style_heading(heading)

    session = data["test_session"]
    result = session["overall_result"]

    p = document.add_paragraph()

    label_run = p.add_run(
        "Overall Result: "
    )

    label_run.bold = True
    label_run.font.name = FONT_NAME

    value_run = p.add_run(
        str(result)
    )

    value_run.bold = True
    value_run.font.name = FONT_NAME
    value_run.font.color.rgb = _status_color(
        result
    )

    if session.get("remarks"):
        remarks_p = document.add_paragraph()

        remarks_label = remarks_p.add_run(
            "Remarks: "
        )

        remarks_label.bold = True
        remarks_label.font.name = FONT_NAME

        remarks_value = remarks_p.add_run(
            session["remarks"]
        )

        remarks_value.font.name = FONT_NAME


# ---------------------------------------------------------------------------
# Review / Approval
# ---------------------------------------------------------------------------

def _format_approval_date(value):
    """
    Convert an approval timestamp into a readable date.

    Supports:
    - Python datetime
    - ISO datetime string
    - None
    """

    if not value:
        return "Pending Approval"

    if isinstance(value, datetime):
        return value.strftime(
            "%d-%m-%Y %H:%M"
        )

    value = str(value)

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        return parsed.strftime(
            "%d-%m-%Y %H:%M"
        )

    except ValueError:
        return value


def _get_reviewer_name(reviewer):
    """
    Build the reviewer display name.

    Expected reviewer structure:

    {
        "user_id": "...",
        "first_name": "...",
        "last_name": "...",
        "designation": "...",
        "email": "..."
    }
    """

    if not reviewer:
        return "Pending Approval"

    first_name = reviewer.get(
        "first_name"
    )

    last_name = reviewer.get(
        "last_name"
    )

    full_name = " ".join(
        part
        for part in [
            first_name,
            last_name
        ]
        if part
    ).strip()

    if full_name:
        return full_name

    return reviewer.get(
        "email",
        "Pending Approval"
    )


def _build_approval_section(
    document,
    data
):
    heading = document.add_heading(
        "6. Review / Approval",
        level=1
    )

    _style_heading(heading)

    # --------------------------------------------------------
    # IMPORTANT:
    # All approval information comes directly from
    # data["report"].
    # --------------------------------------------------------

    report = data.get("report") or {}

    reviewer = report.get(
        "reviewer"
    )

    report_status = str(
        report.get(
            "report_status"
        ) or "GENERATED"
    ).upper()

    reviewer_name = _get_reviewer_name(
        reviewer
    )

    approval_date = _format_approval_date(
        report.get("approved_at")
    )

    if report_status == "APPROVED":
        signature = "Approved electronically"
    else:
        signature = "Pending Approval"

    pairs = [
        (
            "Reviewer",
            reviewer_name
        ),
        (
            "Approval Date",
            approval_date
        ),
        (
            "Report Status",
            report_status
        ),
        (
            "Signature",
            signature
        ),
    ]

    _add_kv_table(
        document,
        pairs,
        label_width=Inches(2.1)
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def create_report(
    data,
    output_path="NAWI_Test_Report.docx"
):
    document = Document()

    section = document.sections[0]

    section.orientation = (
        WD_ORIENT.PORTRAIT
    )

    section.page_width = PAGE_WIDTH
    section.page_height = Inches(11.69)

    section.top_margin = PAGE_MARGIN
    section.bottom_margin = PAGE_MARGIN
    section.left_margin = PAGE_MARGIN
    section.right_margin = PAGE_MARGIN

    section.header_distance = Inches(0.4)
    section.footer_distance = Inches(0.4)

    _apply_base_styles(
        document
    )

    laboratory_name = data[
        "laboratory"
    ]["name"]

    session_number = data[
        "test_session"
    ]["session_number"]

    _add_header(
        section,
        laboratory_name,
        session_number
    )

    _add_page_number_footer(
        section
    )

    _build_masthead(
        document,
        data
    )

    _build_session_section(
        document,
        data
    )

    _build_instrument_section(
        document,
        data
    )

    _build_tester_section(
        document,
        data
    )

    _build_results_section(
        document,
        data
    )

    _build_conclusion_section(
        document,
        data
    )

    _build_approval_section(
        document,
        data
    )

    document.save(
        output_path
    )

    return output_path


if __name__ == "__main__":
    create_report(
        sample_report_data
    )