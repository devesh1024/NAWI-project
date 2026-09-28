from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfbase.pdfmetrics import stringWidth


# ============================================================
# COLORS
# ============================================================

BLUE = colors.HexColor("#315B93")
LIGHT_BLUE = colors.HexColor("#E9EEF6")
BORDER = colors.HexColor("#B8B8B8")
TEXT = colors.HexColor("#222222")
GREEN = colors.HexColor("#3E8E55")
RED = colors.HexColor("#B33A3A")
WHITE = colors.white


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe(value: Any, default: str = "-") -> str:
    """
    Convert values safely to strings for PDF generation.
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return "Yes" if value else "No"

    text = str(value).strip()

    return text if text else default


def format_date(value: Any) -> str:
    """
    Format date/datetime values without making assumptions
    about the source format.
    """
    if value is None:
        return "-"

    # Already a string
    if isinstance(value, str):
        return value

    try:
        return value.strftime("%d-%m-%Y %H:%M")
    except Exception:
        return str(value)


def format_value(value: Any) -> str:
    """
    Display numbers cleanly while preserving meaningful values.
    """
    if value is None:
        return "-"

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"

    return str(value)


def paragraph(
    text: Any,
    style: ParagraphStyle,
) -> Paragraph:
    """
    Small helper for safely creating ReportLab Paragraphs.
    """
    return Paragraph(safe(text), style)


# ============================================================
# STYLES
# ============================================================

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=BLUE,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceAfter=14,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TestHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEXT,
            spaceBefore=5,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=TEXT,
            spaceBefore=7,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=TEXT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmallBold",
            parent=styles["BodySmall"],
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=WHITE,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=TEXT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCellBold",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResultPass",
            parent=styles["TableCellBold"],
            textColor=GREEN,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResultFail",
            parent=styles["TableCellBold"],
            textColor=RED,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Summary",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#444444"),
            spaceBefore=6,
            spaceAfter=5,
        )
    )

    return styles


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def draw_page_header_footer(canvas, doc):
    """
    Draws the header and footer on every page.
    """

    canvas.saveState()

    width, height = A4

    report_data = getattr(doc, "report_data", {}) or {}

    session = report_data.get("test_session") or {}

    session_number = (
        session.get("session_number")
        or session.get("test_session_number")
        or session.get("session_id")
        or "-"
    )

    laboratory = report_data.get("laboratory") or {}

    lab_name = laboratory.get("name") or "Test Laboratory"

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)

    canvas.line(
        doc.leftMargin,
        height - 14 * mm,
        width - doc.rightMargin,
        height - 14 * mm,
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#555555"))

    canvas.drawString(
        doc.leftMargin,
        height - 10.5 * mm,
        f"{lab_name} — NAWI Test Report",
    )

    session_text = f"Session: {safe(session_number)}"

    canvas.drawRightString(
        width - doc.rightMargin,
        height - 10.5 * mm,
        session_text,
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    canvas.setStrokeColor(BORDER)

    canvas.line(
        doc.leftMargin,
        13 * mm,
        width - doc.rightMargin,
        13 * mm,
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#555555"))

    canvas.drawCentredString(
        width / 2,
        8 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# TABLE HELPERS
# ============================================================

def make_table(
    data,
    col_widths=None,
    header=True,
    row_background=True,
    alignments=None,
):
    """
    Creates a consistently styled report table.
    """

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT",
    )

    commands = [
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            BORDER,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    if header:
        commands.extend(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    BLUE,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    WHITE,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
            ]
        )

    if row_background:
        start_row = 1 if header else 0

        for row_index in range(start_row, len(data)):
            if (row_index - start_row) % 2 == 0:
                commands.append(
                    (
                        "BACKGROUND",
                        (0, row_index),
                        (-1, row_index),
                        LIGHT_BLUE,
                    )
                )

    if alignments:
        for column_index, alignment in enumerate(alignments):
            commands.append(
                (
                    "ALIGN",
                    (column_index, 0),
                    (column_index, -1),
                    alignment,
                )
            )

    table.setStyle(TableStyle(commands))

    return table


def make_key_value_table(
    rows,
    col_widths=None,
):
    """
    Creates a two-column key/value table.

    Example:
        [
            ("Manufacturer", "A&D"),
            ("Model", "GX-6000")
        ]
    """

    table_data = []

    for key, value in rows:
        table_data.append(
            [
                Paragraph(
                    safe(key),
                    ParagraphStyle(
                        "kv_key",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        leading=10,
                        textColor=TEXT,
                    ),
                ),
                Paragraph(
                    safe(value),
                    ParagraphStyle(
                        "kv_value",
                        fontName="Helvetica",
                        fontSize=8,
                        leading=10,
                        textColor=TEXT,
                    ),
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=col_widths,
        hAlign="LEFT",
    )

    commands = [
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            BORDER,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "BACKGROUND",
            (0, 0),
            (0, -1),
            LIGHT_BLUE,
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    table.setStyle(TableStyle(commands))

    return table


# ============================================================
# REPORT HEADER
# ============================================================

def build_report_header(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "NAWI TEST REPORT",
            styles["ReportTitle"],
        )
    )

    elements.append(
        Paragraph(
            "Non-Automatic Weighing Instrument — Test Certificate",
            styles["ReportSubtitle"],
        )
    )

    elements.append(
        Table(
            [["", ""]],
            colWidths=[1, 1],
            rowHeights=[1.5],
        )
    )

    # Blue separator
    separator = Table(
        [[""]],
        colWidths=[170 * mm],
        rowHeights=[1.5],
    )

    separator.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    BLUE,
                ),
            ]
        )
    )

    elements.append(separator)
    elements.append(Spacer(1, 8))

    laboratory = data.get("laboratory") or {}
    standard = data.get("standard") or {}
    report = data.get("report") or {}

    left_column = [
        [
            Paragraph(
                "<b>Laboratory:</b> " + safe(laboratory.get("name")),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Address:</b> " + safe(laboratory.get("address")),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Registration No.:</b> "
                + safe(
                    laboratory.get("registration_number")
                    or laboratory.get("registration_no")
                ),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Phone:</b> "
                + safe(
                    laboratory.get("phone")
                    or laboratory.get("phone_number")
                ),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Email:</b> "
                + safe(laboratory.get("email")),
                styles["BodySmall"],
            )
        ],
    ]

    standard_name = (
        standard.get("name")
        or standard.get("standard_name")
        or "OIML R76 — Non-automatic weighing instruments"
    )

    standard_version = (
        standard.get("version")
        or standard.get("edition")
        or standard.get("edition_version")
        or "-"
    )

    right_column = [
        [
            Paragraph(
                "<b>Report No.:</b> "
                + safe(report.get("report_number")),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Report Date:</b> "
                + format_date(
                    report.get("generated_at")
                    or report.get("report_date")
                ),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Standard:</b> " + safe(standard_name),
                styles["BodySmall"],
            )
        ],
        [
            Paragraph(
                "<b>Edition / Version:</b> "
                + safe(standard_version),
                styles["BodySmall"],
            )
        ],
    ]

    left_table = Table(
        left_column,
        colWidths=[82 * mm],
    )

    left_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    right_table = Table(
        right_column,
        colWidths=[82 * mm],
    )

    right_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    info_table = Table(
        [[left_table, right_table]],
        colWidths=[85 * mm, 85 * mm],
    )

    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    elements.append(info_table)
    elements.append(Spacer(1, 8))

    return elements


# ============================================================
# TEST SESSION INFORMATION
# ============================================================

def build_session_information(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "1. Test Session Information",
            styles["SectionHeading"],
        )
    )

    session = data.get("test_session") or {}
    report = data.get("report") or {}

    overall_result = (
        session.get("overall_result")
        or report.get("overall_result")
        or data.get("overall_result")
        or "-"
    )

    rows = [
        [
            Paragraph("Session Number", styles["TableCellBold"]),
            Paragraph(
                safe(
                    session.get("session_number")
                    or session.get("test_session_number")
                ),
                styles["TableCell"],
            ),
        ],
        [
            Paragraph("Application Number", styles["TableCellBold"]),
            Paragraph(
                safe(
                    session.get("application_number")
                    or session.get("application_no")
                ),
                styles["TableCell"],
            ),
        ],
        [
            Paragraph("Test Type", styles["TableCellBold"]),
            Paragraph(
                safe(session.get("test_type") or "NAWI"),
                styles["TableCell"],
            ),
        ],
        [
            Paragraph("Overall Result", styles["TableCellBold"]),
            Paragraph(
                safe(overall_result),
                styles[
                    "ResultPass"
                    if str(overall_result).upper() == "PASS"
                    else (
                        "ResultFail"
                        if str(overall_result).upper() == "FAIL"
                        else "TableCellBold"
                    )
                ],
            ),
        ],
    ]

    table = Table(
        rows,
        colWidths=[50 * mm, 120 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(table)

    return elements


# ============================================================
# INSTRUMENT INFORMATION
# ============================================================

def build_instrument_information(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "2. Instrument Under Test",
            styles["SectionHeading"],
        )
    )

    instrument = data.get("instrument") or {}

    instrument_rows = [
        ("Manufacturer", instrument.get("manufacturer")),
        ("Model", instrument.get("model")),
        (
            "Type Designation",
            instrument.get("type_designation")
            or instrument.get("type"),
        ),
        ("Serial Number", instrument.get("serial_number")),
        (
            "Instrument Type",
            instrument.get("instrument_type"),
        ),
        ("Category", instrument.get("category")),
        ("Accuracy Class", instrument.get("accuracy_class")),
        (
            "Minimum Capacity (Min)",
            instrument.get("minimum_capacity")
            or instrument.get("min_capacity"),
        ),
        (
            "Maximum Capacity (Max)",
            instrument.get("maximum_capacity")
            or instrument.get("max_capacity"),
        ),
        (
            "Scale Interval (d)",
            instrument.get("scale_interval")
            or instrument.get("d"),
        ),
        (
            "Verification Scale Interval (e)",
            instrument.get("verification_scale_interval")
            or instrument.get("e"),
        ),
        (
            "Number of Intervals",
            instrument.get("number_of_intervals")
            or instrument.get("n"),
        ),
        ("Unit", instrument.get("unit")),
    ]

    rows = [
        [
            Paragraph("Specification", styles["TableHeader"]),
            Paragraph("Value", styles["TableHeader"]),
        ]
    ]

    for key, value in instrument_rows:
        rows.append(
            [
                Paragraph(safe(key), styles["TableCellBold"]),
                Paragraph(format_value(value), styles["TableCell"]),
            ]
        )

    table = make_table(
        rows,
        col_widths=[65 * mm, 105 * mm],
        header=True,
    )

    elements.append(table)

    return elements


# ============================================================
# TESTER INFORMATION
# ============================================================

def build_tester_information(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "3. Tester Information",
            styles["SectionHeading"],
        )
    )

    tester = data.get("tester") or {}

    first_name = tester.get("first_name") or ""
    last_name = tester.get("last_name") or ""

    full_name = tester.get("name")

    if not full_name:
        full_name = f"{first_name} {last_name}".strip()

    rows = [
        ("Name", full_name),
        ("Designation", tester.get("designation")),
    ]

    elements.append(
        make_key_value_table(
            rows,
            col_widths=[50 * mm, 120 * mm],
        )
    )

    return elements


# ============================================================
# OBSERVATIONS
# ============================================================

def build_observations(observations, styles):
    elements = []

    elements.append(
        Paragraph(
            "Observations",
            styles["SubHeading"],
        )
    )

    if not observations:
        elements.append(
            Paragraph(
                "No observations recorded.",
                styles["BodySmall"],
            )
        )
        return elements

    rows = [
        [
            Paragraph("Parameter", styles["TableHeader"]),
            Paragraph("Value", styles["TableHeader"]),
            Paragraph("Unit", styles["TableHeader"]),
        ]
    ]

    for observation in observations:
        parameter = (
            observation.get("parameter")
            or observation.get("parameter_name")
            or observation.get("name")
            or observation.get("field")
            or "-"
        )

        value =(
            observation.get("value_numeric")
            if observation.get("value_numeric") is not None
            else (
                observation.get("value")
                if observation.get("value") is not None
                else observation.get("observed_value")
            )
        )

        unit = observation.get("unit") or "-"

        rows.append(
            [
                Paragraph(safe(parameter), styles["TableCell"]),
                Paragraph(format_value(value), styles["TableCell"]),
                Paragraph(safe(unit), styles["TableCell"]),
            ]
        )

    elements.append(
        make_table(
            rows,
            col_widths=[75 * mm, 60 * mm, 35 * mm],
            header=True,
            alignments=["LEFT", "CENTER", "CENTER"],
        )
    )

    return elements


# ============================================================
# CALCULATIONS
# ============================================================

def build_calculations(calculations, styles):
    elements = []

    elements.append(
        Paragraph(
            "Calculations",
            styles["SubHeading"],
        )
    )

    if not calculations:
        elements.append(
            Paragraph(
                "No calculations recorded.",
                styles["BodySmall"],
            )
        )
        return elements

    rows = [
        [
            Paragraph("Calculation", styles["TableHeader"]),
            Paragraph("Calculated Value", styles["TableHeader"]),
            Paragraph("Unit", styles["TableHeader"]),
            Paragraph("Formula", styles["TableHeader"]),
        ]
    ]

    for calculation in calculations:
        calculation_name = (
            calculation.get("calculation")
            or calculation.get("calculation_name")
            or calculation.get("name")
            or calculation.get("calculation_type")
            or calculation.get("code")
            or "-"
        )

        calculated_value = (
            calculation.get("calculated_value")
            if calculation.get("calculated_value") is not None
            else calculation.get("value")
        )

        unit = calculation.get("unit") or "-"

        formula = (
            calculation.get("formula")
            or calculation.get("calculation_type")
            or "-"
        )

        rows.append(
            [
                Paragraph(safe(calculation_name), styles["TableCell"]),
                Paragraph(
                    format_value(calculated_value),
                    styles["TableCell"],
                ),
                Paragraph(safe(unit), styles["TableCell"]),
                Paragraph(safe(formula), styles["TableCell"]),
            ]
        )

    elements.append(
        make_table(
            rows,
            col_widths=[45 * mm, 45 * mm, 25 * mm, 55 * mm],
            header=True,
            alignments=["LEFT", "CENTER", "CENTER", "LEFT"],
        )
    )

    return elements


# ============================================================
# RESULT
# ============================================================

def build_result(result, styles):
    elements = []

    elements.append(
        Paragraph(
            "Result",
            styles["SubHeading"],
        )
    )

    if not result:
        elements.append(
            Paragraph(
                "No result recorded.",
                styles["BodySmall"],
            )
        )
        return elements

    result_rows = [
        (
            "Measured Value",
            result.get("measured_value"),
        ),
        (
            "MPE",
            result.get("mpe"),
        ),
        (
            "Error",
            result.get("error"),
        ),
        (
            "Corrected Error",
            result.get("corrected_error"),
        ),
        (
            "Acceptance Condition",
            result.get("acceptance_condition"),
        ),
        (
            "Result",
            result.get("result") or result.get("status"),
        ),
    ]

    rows = [
        [
            Paragraph("Field", styles["TableHeader"]),
            Paragraph("Value", styles["TableHeader"]),
        ]
    ]

    for key, value in result_rows:

        result_text = format_value(value)

        if key == "Result":
            result_upper = result_text.upper()

            if result_upper == "PASS":
                value_style = styles["ResultPass"]
            elif result_upper == "FAIL":
                value_style = styles["ResultFail"]
            else:
                value_style = styles["TableCellBold"]
        else:
            value_style = styles["TableCell"]

        rows.append(
            [
                Paragraph(safe(key), styles["TableCellBold"]),
                Paragraph(result_text, value_style),
            ]
        )

    elements.append(
        make_table(
            rows,
            col_widths=[50 * mm, 120 * mm],
            header=True,
        )
    )

    summary = result.get("summary")

    if summary:
        elements.append(
            Paragraph(
                f"<b>Summary:</b> {safe(summary)}",
                styles["Summary"],
            )
        )

    return elements


# ============================================================
# INDIVIDUAL TEST BLOCK
# ============================================================

def build_test_block(test, index, styles):
    elements = []

    test_name = (
    test.get("test_name")
    or test.get("test_code")
    or test.get("name")
    or test.get("test_definition_name")
    or test.get("test_definition_code")
    or f"Test {index}"
    )

    elements.append(
        Paragraph(
            f"Test {index} — {safe(test_name)}",
            styles["TestHeading"],
        )
    )

    # --------------------------------------------------------
    # TEST RESULT STATUS
    # --------------------------------------------------------

    test_result = test.get("result")

    # The sample/API structure stores the detailed result
    # inside the "results" list.
    detailed_results = test.get("results") or []

    detailed_result = (
        detailed_results[0]
        if detailed_results
        and isinstance(detailed_results[0], dict)
        else {}
    )

    # --------------------------------------------------------
    # N/A TEST
    # --------------------------------------------------------

    if str(test_result).upper() in {
        "N/A",
        "NA",
        "NOT APPLICABLE",
    }:

        reason = (
            test.get("na_reason")
            or "Not applicable"
        )

        na_table = make_key_value_table(
            [
                ("Result", "N/A"),
                ("Reason", reason),
            ],
            col_widths=[50 * mm, 120 * mm],
        )

        elements.append(na_table)

        return elements

    # --------------------------------------------------------
    # OBSERVATIONS
    # --------------------------------------------------------

    observations = test.get("observations") or []

    elements.extend(
        build_observations(
            observations,
            styles,
        )
    )

    elements.append(Spacer(1, 4))

    # --------------------------------------------------------
    # CALCULATIONS
    # --------------------------------------------------------

    calculations = test.get("calculations") or []

    elements.extend(
        build_calculations(
            calculations,
            styles,
        )
    )

    elements.append(Spacer(1, 4))

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if detailed_result:
        result = detailed_result

        # Convert API/sample field names into the names
        # expected by build_result().
        result = {
            "measured_value": result.get("measured_value"),
            "mpe": result.get("mpe_value"),
            "error": result.get("error_value"),
            "corrected_error": result.get("corrected_error"),
            "acceptance_condition": result.get(
                "acceptance_condition"
            ),
            "result": result.get("pass_fail"),
            "summary": result.get("result_summary"),
        }

        elements.extend(
            build_result(
                result,
                styles,
            )
        )

    else:
        elements.append(
            Paragraph(
                "No detailed result recorded.",
                styles["BodySmall"],
            )
        )

    elements.append(Spacer(1, 6))

    return elements

    # --------------------------------------------------------
    # OBSERVATIONS
    # --------------------------------------------------------

    observations = test.get("observations") or []

    elements.extend(
        build_observations(
            observations,
            styles,
        )
    )

    elements.append(Spacer(1, 4))

    # --------------------------------------------------------
    # CALCULATIONS
    # --------------------------------------------------------

    calculations = test.get("calculations") or []

    elements.extend(
        build_calculations(
            calculations,
            styles,
        )
    )

    elements.append(Spacer(1, 4))

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = test.get("result")

    if not isinstance(result, dict):
        result = {}

    elements.extend(
        build_result(
            result,
            styles,
        )
    )

    elements.append(Spacer(1, 6))

    return elements


# ============================================================
# TEST RESULTS SECTION
# ============================================================

def build_test_results(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "4. Test Results",
            styles["SectionHeading"],
        )
    )

    tests = data.get("tests") or []

    if not tests:
        elements.append(
            Paragraph(
                "No tests recorded.",
                styles["BodySmall"],
            )
        )

        return elements

    for index, test in enumerate(tests, start=1):

        test_elements = build_test_block(
            test,
            index,
            styles,
        )

        elements.extend(test_elements)

        # Add spacing between tests
        if index < len(tests):
            elements.append(Spacer(1, 8))

    return elements


# ============================================================
# OVERALL CONCLUSION
# ============================================================

def build_conclusion(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "5. Overall Conclusion",
            styles["SectionHeading"],
        )
    )

    session = data.get("test_session") or {}
    report = data.get("report") or {}

    overall_result = (
        report.get("overall_result")
        or session.get("overall_result")
        or data.get("overall_result")
        or "-"
    )

    remarks = (
        report.get("remarks")
        or session.get("remarks")
        or data.get("remarks")
        or "-"
    )

    result_upper = str(overall_result).upper()

    if result_upper == "PASS":
        result_style = styles["ResultPass"]
    elif result_upper == "FAIL":
        result_style = styles["ResultFail"]
    else:
        result_style = styles["BodySmallBold"]

    elements.append(
        Paragraph(
            "Overall Result: "
            + f'<font color="{result_style.textColor.hexval()}">'
            + f"<b>{safe(overall_result)}</b>"
            + "</font>",
            styles["BodySmall"],
        )
    )

    elements.append(Spacer(1, 4))

    elements.append(
        Paragraph(
            "<b>Remarks:</b> " + safe(remarks),
            styles["BodySmall"],
        )
    )

    return elements


# ============================================================
# REVIEW / APPROVAL
# ============================================================

def build_approval(data, styles):
    elements = []

    elements.append(
        Paragraph(
            "6. Review / Approval",
            styles["SectionHeading"],
        )
    )

    report = data.get("report") or {}

    reviewer = report.get("reviewer") or {}

    reviewer_name = reviewer.get("name")

    if not reviewer_name:
        first_name = reviewer.get("first_name") or ""
        last_name = reviewer.get("last_name") or ""
        reviewer_name = f"{first_name} {last_name}".strip()

    if not reviewer_name:
        reviewer_name = (
            report.get("reviewer_name")
            or report.get("approved_by_name")
            or "-"
        )

    approval_date = (
        report.get("approved_at")
        or report.get("approval_date")
        or "-"
    )

    report_status = (
        report.get("report_status")
        or report.get("status")
        or "GENERATED"
    )

    if str(report_status).upper() == "APPROVED":
        signature = "Approved electronically"
    else:
        signature = "Pending Approval"

    rows = [
        ("Reviewer", reviewer_name),
        ("Approval Date", format_date(approval_date)),
        ("Report Status", report_status),
        ("Signature", signature),
    ]

    elements.append(
        make_key_value_table(
            rows,
            col_widths=[50 * mm, 120 * mm],
        )
    )

    return elements


# ============================================================
# MAIN PDF CREATOR
# ============================================================

def create_pdf(
    data: dict,
    output_path: str = "NAWI_Test_Report.pdf",
):
    """
    Generate a NAWI PDF report from the same structured report
    data used by the DOCX generator.

    Parameters
    ----------
    data:
        Structured report data returned by the report-data API.

    output_path:
        Destination path for the generated PDF.

    Returns
    -------
    str:
        Absolute path to the generated PDF.
    """

    if not isinstance(data, dict):
        raise TypeError("Report data must be a dictionary.")

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    styles = build_styles()

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="NAWI Test Report",
        author="NAWI Report Generation System",
        subject="Non-Automatic Weighing Instrument Test Report",
    )

    # Store data on document so page header/footer can access it.
    document.report_data = data

    story = []

    # --------------------------------------------------------
    # PAGE 1
    # --------------------------------------------------------

    story.extend(
        build_report_header(
            data,
            styles,
        )
    )

    story.extend(
        build_session_information(
            data,
            styles,
        )
    )

    story.append(Spacer(1, 4))

    story.extend(
        build_instrument_information(
            data,
            styles,
        )
    )

    story.append(Spacer(1, 4))

    story.extend(
        build_tester_information(
            data,
            styles,
        )
    )

    # --------------------------------------------------------
    # PAGE BREAK
    #
    # The current DOCX reference naturally has the Test Results
    # section starting on page 2, so we deliberately preserve
    # that structure here.
    # --------------------------------------------------------

    story.append(PageBreak())

    # --------------------------------------------------------
    # PAGE 2
    # --------------------------------------------------------

    story.extend(
        build_test_results(
            data,
            styles,
        )
    )

    story.append(Spacer(1, 6))

    story.extend(
        build_conclusion(
            data,
            styles,
        )
    )

    story.append(Spacer(1, 4))

    story.extend(
        build_approval(
            data,
            styles,
        )
    )

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(
        story,
        onFirstPage=draw_page_header_footer,
        onLaterPages=draw_page_header_footer,
    )

    return str(output_path.resolve())


# ============================================================
# OPTIONAL LOCAL TEST
# ============================================================

if __name__ == "__main__":
    """
    Optional standalone test.

    This expects sample_report_data.py to contain:

        SAMPLE_REPORT_DATA

    If your sample file uses a different variable name,
    simply change the import below.
    """

    try:
        from .sample_report_data import SAMPLE_REPORT_DATA

        output = create_pdf(
            SAMPLE_REPORT_DATA,
            output_path="NAWI_Test_Report.pdf",
        )

        print(f"PDF generated successfully:")
        print(output)

    except ImportError as error:
        print(
            "Could not import SAMPLE_REPORT_DATA from "
            "sample_report_data.py"
        )
        print(error)