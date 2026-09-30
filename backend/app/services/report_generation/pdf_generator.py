from pathlib import Path
from typing import Any
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo

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


# ============================================================
# THEME
# ============================================================

BURGUNDY = colors.HexColor("#6B2D2D")
BURGUNDY_DARK = colors.HexColor("#4B2020")
BURGUNDY_LIGHT = colors.HexColor("#F4EAEA")
CHARCOAL = colors.HexColor("#2E2E2E")
TEXT = colors.HexColor("#252525")
MUTED = colors.HexColor("#666666")
BORDER = colors.HexColor("#B7B0B0")
ROW_ALT = colors.HexColor("#FAF7F7")
WHITE = colors.white
GREEN = colors.HexColor("#2F6B3A")
RED = colors.HexColor("#9B3030")
GREY = colors.HexColor("#6E6E6E")

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
UTC = timezone.utc


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe(value: Any, default: str = "Not recorded") -> str:
    """Convert a value into clean report text without placeholder dashes."""
    if value is None:
        return default

    if isinstance(value, bool):
        return "Yes" if value else "No"

    text = str(value).strip()
    return text if text else default


def optional(value: Any, default: str = "") -> str:
    """Return a blank string for absent optional fields."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return default


def format_value(value: Any) -> str:
    if value is None:
        return "Not recorded"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"

    return str(value)


def parse_datetime(value: Any) -> datetime | None:
    """Parse common datetime forms and normalize to IST.

    Naive timestamps from the backend are treated as UTC because the
    report service stores approval/generated timestamps in UTC and some
    database datetime columns may arrive without a timezone marker.
    Aware timestamps are converted using the actual offset.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            # Fall back to common display formats.
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y %H:%M",
            ):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(IST)


def format_datetime(value: Any, include_time: bool = True) -> str:
    dt = parse_datetime(value)
    if dt is None:
        return "Not recorded"
    return dt.strftime("%d-%m-%Y %H:%M IST" if include_time else "%d-%m-%Y")


def display_timestamp(value: Any) -> str:
    return format_datetime(value, include_time=True)


def get_tester_name(tester: dict) -> str:
    name = first_present(tester.get("name"), tester.get("full_name"))
    if name:
        return str(name)
    first_name = tester.get("first_name") or ""
    last_name = tester.get("last_name") or ""
    return f"{first_name} {last_name}".strip() or "Not recorded"


def get_reviewer_name(report: dict) -> str:
    reviewer = report.get("reviewer") or {}
    name = first_present(
        reviewer.get("name"),
        report.get("reviewer_name"),
        report.get("approved_by_name"),
    )
    if name:
        return str(name)
    first_name = reviewer.get("first_name") or ""
    last_name = reviewer.get("last_name") or ""
    return f"{first_name} {last_name}".strip() or "Not recorded"


def get_test_result(test: dict) -> str:
    test_result = first_present(test.get("result"), test.get("pass_fail"))
    if test_result:
        return str(test_result)

    details = test.get("results") or []
    if details and isinstance(details[0], dict):
        return safe(details[0].get("pass_fail"), "Not recorded")

    return "Not recorded"


def get_applicability(test: dict) -> str:
    return str(
        first_present(
            test.get("applicability_status"),
            test.get("applicability"),
            default="Not recorded",
        )
    )


def get_detailed_result(test: dict) -> dict:
    results = test.get("results") or []
    for item in results:
        if isinstance(item, dict):
            return item
    return {}


def result_style_name(result_text: str, styles: dict) -> str:
    upper = str(result_text).upper()
    if upper == "PASS":
        return "ResultPass"
    if upper == "FAIL":
        return "ResultFail"
    return "TableCellBold"


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
            fontSize=17,
            leading=20,
            alignment=TA_CENTER,
            textColor=BURGUNDY_DARK,
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=9,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=BURGUNDY_DARK,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TestHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=CHARCOAL,
            spaceBefore=5,
            spaceAfter=4,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10.5,
            textColor=CHARCOAL,
            spaceBefore=4,
            spaceAfter=3,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=9.5,
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
            fontSize=7.1,
            leading=8.5,
            textColor=WHITE,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=8.8,
            textColor=TEXT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCellCenter",
            parent=styles["TableCell"],
            alignment=TA_CENTER,
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
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResultFail",
            parent=styles["TableCellBold"],
            textColor=RED,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Notice",
            parent=styles["BodySmall"],
            fontSize=7.2,
            leading=9,
            textColor=CHARCOAL,
        )
    )

    return styles


# ============================================================
# TABLE HELPERS
# ============================================================

def P(text: Any, style):
    return Paragraph(safe(text), style)


def make_table(
    data,
    col_widths=None,
    header=True,
    row_background=True,
    alignments=None,
    repeat_rows=1,
    header_background=BURGUNDY,
):
    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=repeat_rows if header else 0,
        hAlign="LEFT",
    )

    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_background),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ]
        )

    if row_background:
        start_row = 1 if header else 0
        for row_index in range(start_row, len(data)):
            if (row_index - start_row) % 2 == 1:
                commands.append(
                    ("BACKGROUND", (0, row_index), (-1, row_index), ROW_ALT)
                )

    if alignments:
        for column_index, alignment in enumerate(alignments):
            commands.append(
                ("ALIGN", (column_index, 0), (column_index, -1), alignment)
            )

    table.setStyle(TableStyle(commands))
    return table


def make_key_value_table(rows, styles, col_widths=None):
    data = []
    for key, value in rows:
        data.append(
            [
                Paragraph(safe(key), styles["TableCellBold"]),
                Paragraph(safe(value), styles["TableCell"]),
            ]
        )

    table = Table(data, colWidths=col_widths or [48 * mm, 122 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, -1), BURGUNDY_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def draw_page_header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    data = getattr(doc, "report_data", {}) or {}

    lab = data.get("laboratory") or {}
    session = data.get("test_session") or {}
    report = data.get("report") or {}

    lab_name = optional(lab.get("name"), "Testing Laboratory")
    report_no = optional(report.get("report_number"), "Report No. not assigned")
    app_no = optional(session.get("application_number"), "Application not assigned")

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(doc.leftMargin, height - 12 * mm, width - doc.rightMargin, height - 12 * mm)

    canvas.setFont("Helvetica-Bold", 7.1)
    canvas.setFillColor(CHARCOAL)
    canvas.drawString(
        doc.leftMargin,
        height - 9 * mm,
        "NAWI TEST REPORT",
    )

    canvas.setFont("Helvetica", 6.9)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        width - doc.rightMargin,
        height - 9 * mm,
        f"{lab_name} | {report_no} | {app_no}",
    )

    canvas.setStrokeColor(BORDER)
    canvas.line(doc.leftMargin, 13 * mm, width - doc.rightMargin, 13 * mm)

    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 8.5 * mm, "Controlled report copy")
    canvas.drawRightString(width - doc.rightMargin, 8.5 * mm, "NAWI Test & Compliance System")
    canvas.drawCentredString(width / 2, 8.5 * mm, f"Page {doc.page}")

    canvas.restoreState()


# ============================================================
# REPORT HEADER / FIRST PAGE
# ============================================================

def build_report_header(data, styles):
    elements = []
    laboratory = data.get("laboratory") or {}
    standard = data.get("standard") or {}
    report = data.get("report") or {}
    session = data.get("test_session") or {}
    instrument = data.get("instrument") or {}

    logo = Table(
        [[
            Paragraph(
                "<b>LOGO</b><br/><font size='6'>Reserved for official logo</font>",
                styles["BodySmall"],
            )
        ]],
        colWidths=[27 * mm],
        rowHeights=[21 * mm],
    )
    logo.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.55, BORDER),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    org_name = safe(laboratory.get("name"), "TESTING LABORATORY")
    org_address = safe(laboratory.get("address"), "Not recorded")
    location = " / ".join(
        part for part in (
            laboratory.get("city"),
            laboratory.get("state"),
            laboratory.get("pincode"),
        ) if part
    )
    contact = " | ".join(
        str(v) for v in (laboratory.get("phone"), laboratory.get("email")) if v
    )

    org_block = [
        Paragraph(f"<b>{org_name}</b>", ParagraphStyle(
            "OrgName", parent=styles["BodySmall"], fontName="Helvetica-Bold",
            fontSize=11.2, leading=13.5, alignment=TA_CENTER,
        )),
        Paragraph(org_address, ParagraphStyle(
            "OrgAddress", parent=styles["BodySmall"], fontSize=7.2,
            leading=8.8, alignment=TA_CENTER,
        )),
    ]
    if location:
        org_block.append(
            Paragraph(location, ParagraphStyle(
                "OrgLocation", parent=styles["BodySmall"], fontSize=7.2,
                leading=8.8, alignment=TA_CENTER,
            ))
        )
    if contact:
        org_block.append(
            Paragraph(contact, ParagraphStyle(
                "OrgContact", parent=styles["BodySmall"], fontSize=6.8,
                leading=8.2, alignment=TA_CENTER,
            ))
        )

    masthead = Table(
        [[logo, org_block]],
        colWidths=[32 * mm, 138 * mm],
        hAlign="LEFT",
    )
    masthead.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(masthead)
    elements.append(Spacer(1, 5))

    elements.append(Paragraph("NON-AUTOMATIC WEIGHING INSTRUMENTS", styles["ReportSubtitle"]))
    elements.append(Paragraph("NAWI TEST REPORT", styles["ReportTitle"]))
    elements.append(Paragraph("Formal test and evaluation record", styles["ReportSubtitle"]))

    report_date = first_present(report.get("report_date"), report.get("generated_at"))
    report_meta = [
        [P("Report No.", styles["TableCellBold"]), P(report.get("report_number"), styles["TableCell"]),
         P("Report Date", styles["TableCellBold"]), P(format_datetime(report_date, False) if report_date else "Not recorded", styles["TableCell"])],
        [P("Report Version", styles["TableCellBold"]), P(report.get("report_version") or report.get("version"), styles["TableCell"]),
         P("Report Status", styles["TableCellBold"]), P(report.get("report_status") or report.get("status"), styles["TableCell"])],
        [P("Application No.", styles["TableCellBold"]), P(session.get("application_number"), styles["TableCell"]),
         P("Test Session No.", styles["TableCellBold"]), P(session.get("session_number"), styles["TableCell"])],
        [P("Applicable Standard", styles["TableCellBold"]), P(
            first_present(standard.get("standard_code"), standard.get("title"), "OIML R 76"), styles["TableCell"]),
         P("Type Designation", styles["TableCellBold"]), P(instrument.get("type_designation"), styles["TableCell"])],
    ]
    report_table = make_table(
        report_meta,
        col_widths=[31 * mm, 54 * mm, 31 * mm, 54 * mm],
        header=False,
        row_background=False,
    )
    report_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BURGUNDY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), BURGUNDY_LIGHT),
    ]))
    elements.append(report_table)
    elements.append(Spacer(1, 4))

    standard_version = first_present(standard.get("version"), standard.get("edition_year"))
    overall = first_present(report.get("overall_result"), session.get("overall_result"), data.get("overall_result"))
    summary_row = [
        P("Standard Edition / Version", styles["TableCellBold"]),
        P(standard_version, styles["TableCell"]),
        P("Overall Result", styles["TableCellBold"]),
        Paragraph(
            safe(overall),
            styles[result_style_name(safe(overall), styles)],
        ),
    ]
    summary = make_table([summary_row], col_widths=[45 * mm, 40 * mm, 35 * mm, 50 * mm], header=False, row_background=False)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BURGUNDY_LIGHT),
        ("BACKGROUND", (2, 0), (2, 0), BURGUNDY_LIGHT),
    ]))
    elements.append(summary)

    return elements


# ============================================================
# SECTION 1 - LABORATORY
# ============================================================

def build_laboratory_information(data, styles):
    lab = data.get("laboratory") or {}
    rows = [
        ("Laboratory Code", first_present(lab.get("laboratory_code"), lab.get("code"))),
        ("Registration No.", lab.get("registration_number")),
        ("Laboratory Name", lab.get("name")),
        ("Address", lab.get("address")),
        ("City / State / PIN", " / ".join(str(v) for v in (lab.get("city"), lab.get("state"), lab.get("pincode")) if v)),
        ("Country", lab.get("country")),
        ("Phone", lab.get("phone")),
        ("Email", lab.get("email")),
    ]
    return [Paragraph("1. Laboratory Information", styles["SectionHeading"]), make_key_value_table(rows, styles)]


# ============================================================
# SECTION 2 - INSTRUMENT
# ============================================================

def build_instrument_information(data, styles):
    instrument = data.get("instrument") or {}
    rows = [
        [P("Specification", styles["TableHeader"]), P("Value", styles["TableHeader"]),
         P("Specification", styles["TableHeader"]), P("Value", styles["TableHeader"])],
    ]

    pairs = [
        ("Instrument Code", instrument.get("instrument_code"), "Manufacturer", instrument.get("manufacturer")),
        ("Model", instrument.get("model"), "Type Designation", instrument.get("type_designation") or instrument.get("type")),
        ("Serial Number", instrument.get("serial_number"), "Instrument Type", instrument.get("instrument_type")),
        ("Category", instrument.get("category"), "Accuracy Class", instrument.get("accuracy_class")),
        ("Minimum Capacity (Min)", first_present(instrument.get("minimum_capacity"), instrument.get("min_capacity")),
         "Maximum Capacity (Max)", first_present(instrument.get("maximum_capacity"), instrument.get("max_capacity"))),
        ("Scale Interval (d)", first_present(instrument.get("scale_interval"), instrument.get("d")),
         "Verification Scale Interval (e)", first_present(instrument.get("verification_scale_interval"), instrument.get("e"))),
        ("Number of Intervals (n)", first_present(instrument.get("number_of_intervals"), instrument.get("n")),
         "Unit", instrument.get("unit")),
        ("Indication Type", instrument.get("indication_type"), "Software / Firmware", instrument.get("software_firmware") or instrument.get("software_version")),
    ]

    for left_key, left_value, right_key, right_value in pairs:
        rows.append([
            P(left_key, styles["TableCellBold"]), P(format_value(left_value), styles["TableCell"]),
            P(right_key, styles["TableCellBold"]), P(format_value(right_value), styles["TableCell"]),
        ])

    table = make_table(rows, col_widths=[32 * mm, 53 * mm, 37 * mm, 48 * mm], header=True, row_background=True)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 1), (0, -1), BURGUNDY_LIGHT),
        ("BACKGROUND", (2, 1), (2, -1), BURGUNDY_LIGHT),
    ]))
    return [Paragraph("2. Instrument Under Test", styles["SectionHeading"]), table]


# ============================================================
# SECTION 3 - TESTER / SESSION
# ============================================================

def build_session_information(data, styles):
    session = data.get("test_session") or {}
    report = data.get("report") or {}
    tester = data.get("tester") or {}
    overall = first_present(report.get("overall_result"), session.get("overall_result"), data.get("overall_result"))

    rows = [
        [P("Session No.", styles["TableCellBold"]), P(first_present(session.get("session_number"), session.get("test_session_number")), styles["TableCell"]),
         P("Application No.", styles["TableCellBold"]), P(first_present(session.get("application_number"), session.get("application_no")), styles["TableCell"])],
        [P("Test Type", styles["TableCellBold"]), P(session.get("test_type") or "NAWI", styles["TableCell"]),
         P("Session Status", styles["TableCellBold"]), P(session.get("status"), styles["TableCell"])],
        [P("Tester", styles["TableCellBold"]), P(get_tester_name(tester), styles["TableCell"]),
         P("Designation", styles["TableCellBold"]), P(tester.get("designation"), styles["TableCell"])],
        [P("Test Started", styles["TableCellBold"]), P(display_timestamp(session.get("started_at") or session.get("start_date")), styles["TableCell"]),
         P("Test Completed", styles["TableCellBold"]), P(display_timestamp(session.get("completed_at") or session.get("completion_date")), styles["TableCell"])],
        [P("Overall Result", styles["TableCellBold"]), Paragraph(safe(overall), styles[result_style_name(safe(overall), styles)]),
         P("Tester ID", styles["TableCellBold"]), P(first_present(tester.get("employee_id"), tester.get("user_id")), styles["TableCell"])],
    ]
    table = make_table(rows, col_widths=[28 * mm, 57 * mm, 32 * mm, 53 * mm], header=False, row_background=False)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BURGUNDY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), BURGUNDY_LIGHT),
    ]))
    return [Paragraph("3. Tester / Test Session Information", styles["SectionHeading"]), table]


# ============================================================
# SECTION 4 - TEST EQUIPMENT
# ============================================================

def build_test_equipment(data, styles):
    equipment = data.get("test_equipment") or []
    heading = Paragraph("4. Test Equipment", styles["SectionHeading"])

    if not equipment:
        table = make_key_value_table(
            [("Record", "No test equipment information was recorded in the report data.")],
            styles,
            col_widths=[35 * mm, 135 * mm],
        )
        return [heading, table]

    rows = [[
        P("Equipment ID", styles["TableHeader"]),
        P("Equipment", styles["TableHeader"]),
        P("Model", styles["TableHeader"]),
        P("Serial / Identification", styles["TableHeader"]),
        P("Calibration", styles["TableHeader"]),
    ]]

    for item in equipment:
        rows.append([
            P(first_present(item.get("equipment_code"), item.get("identification_number")), styles["TableCell"]),
            P(first_present(item.get("equipment_name"), item.get("name")), styles["TableCell"]),
            P(item.get("model"), styles["TableCell"]),
            P(first_present(item.get("serial_number"), item.get("identification_number")), styles["TableCell"]),
            P(item.get("calibration_status"), styles["TableCellCenter"]),
        ])

    table = make_table(rows, col_widths=[27 * mm, 45 * mm, 31 * mm, 37 * mm, 30 * mm], header=True, alignments=["LEFT", "LEFT", "LEFT", "LEFT", "CENTER"])
    due_notes = []
    for item in equipment:
        due = item.get("calibration_due_date")
        if due:
            due_notes.append(f"{first_present(item.get('equipment_code'), item.get('equipment_name'), default='Equipment')}: due {format_datetime(due, False)}")
    note = " ; ".join(due_notes)
    result = [heading, table]
    if note:
        result.append(Paragraph(note, styles["BodySmall"]))
    return result


# ============================================================
# SECTION 5 - ENVIRONMENT
# ============================================================

def build_environmental_conditions(data, styles):
    conditions = data.get("environmental_conditions") or []
    heading = Paragraph("5. Environmental Conditions", styles["SectionHeading"])

    if not conditions:
        table = make_key_value_table(
            [("Record", "No environmental conditions were recorded in the report data.")],
            styles,
            col_widths=[35 * mm, 135 * mm],
        )
        return [heading, table]

    start = conditions[0]
    end = conditions[-1]

    def env_value(item, field, unit):
        value = item.get(field)
        return f"{format_value(value)} {unit}" if value is not None else "Not recorded"

    rows = [
        [P("Parameter", styles["TableHeader"]), P("Start", styles["TableHeader"]), P("End", styles["TableHeader"]), P("Recorded At", styles["TableHeader"])],
        [P("Temperature", styles["TableCellBold"]), P(env_value(start, "temperature", "°C"), styles["TableCellCenter"]), P(env_value(end, "temperature", "°C"), styles["TableCellCenter"]), P(display_timestamp(start.get("recorded_at")), styles["TableCell"])],
        [P("Relative Humidity", styles["TableCellBold"]), P(env_value(start, "humidity", "%"), styles["TableCellCenter"]), P(env_value(end, "humidity", "%"), styles["TableCellCenter"]), P(display_timestamp(end.get("recorded_at")), styles["TableCell"])],
        [P("Atmospheric Pressure", styles["TableCellBold"]), P(env_value(start, "pressure", "hPa"), styles["TableCellCenter"]), P(env_value(end, "pressure", "hPa"), styles["TableCellCenter"]), P("", styles["TableCell"])],
    ]
    table = make_table(rows, col_widths=[40 * mm, 32 * mm, 32 * mm, 66 * mm], header=True, alignments=["LEFT", "CENTER", "CENTER", "LEFT"])

    source = first_present(end.get("source"), start.get("source"))
    remarks = first_present(end.get("remarks"), start.get("remarks"))
    footer = []
    if source:
        footer.append(f"Monitoring source: {source}")
    if remarks:
        footer.append(f"Remarks: {remarks}")
    result = [heading, table]
    if footer:
        result.append(Paragraph(" | ".join(footer), styles["BodySmall"]))
    return result


# ============================================================
# SECTION 6 - SUMMARY
# ============================================================

def build_test_summary(data, styles):
    tests = data.get("tests") or []
    rows = [[
        P("No.", styles["TableHeader"]),
        P("Code", styles["TableHeader"]),
        P("Test / Examination", styles["TableHeader"]),
        P("Applicability", styles["TableHeader"]),
        P("Result", styles["TableHeader"]),
        P("Remarks", styles["TableHeader"]),
    ]]

    counts = {"APPLICABLE": 0, "PASS": 0, "FAIL": 0, "N/A": 0}

    for index, test in enumerate(tests, start=1):
        code = first_present(test.get("test_code"), test.get("code"), default="Not recorded")
        name = first_present(test.get("test_name"), test.get("name"), test.get("test_definition_name"), default=f"Test {index}")
        applicability = get_applicability(test)
        result = get_test_result(test)
        na_reason = test.get("na_reason") if str(result).upper() in {"N/A", "NA", "NOT APPLICABLE"} else None

        if applicability.upper() in {"APPLICABLE", "YES"}:
            counts["APPLICABLE"] += 1
        if result.upper() == "PASS":
            counts["PASS"] += 1
        elif result.upper() == "FAIL":
            counts["FAIL"] += 1
        elif result.upper() in {"N/A", "NA", "NOT APPLICABLE"}:
            counts["N/A"] += 1

        rows.append([
            P(index, styles["TableCellCenter"]),
            P(code, styles["TableCell"]),
            P(name, styles["TableCell"]),
            P(applicability, styles["TableCellCenter"]),
            Paragraph(safe(result), styles[result_style_name(safe(result), styles)]),
            P(na_reason or "", styles["TableCell"]),
        ])

    if not tests:
        rows.append([
            P("", styles["TableCell"]), P("", styles["TableCell"]),
            P("No tests recorded.", styles["TableCell"]), P("", styles["TableCell"]),
            P("", styles["TableCell"]), P("", styles["TableCell"]),
        ])

    table = make_table(
        rows,
        col_widths=[10 * mm, 25 * mm, 62 * mm, 27 * mm, 22 * mm, 24 * mm],
        header=True,
        alignments=["CENTER", "LEFT", "LEFT", "CENTER", "CENTER", "LEFT"],
    )

    stats = (
        f"Tests recorded: {len(tests)} | Applicable: {counts['APPLICABLE']} | "
        f"PASS: {counts['PASS']} | FAIL: {counts['FAIL']} | N/A: {counts['N/A']}"
    )
    return [Paragraph("6. Summary of Test Results", styles["SectionHeading"]), table, Spacer(1, 3), Paragraph(stats, styles["BodySmallBold"])]


# ============================================================
# TEST DETAIL HELPERS
# ============================================================

def build_observations(observations, styles):
    elements = [Paragraph("Observations", styles["SubHeading"])]
    if not observations:
        elements.append(Paragraph("No observations recorded.", styles["BodySmall"]))
        return elements

    rows = [[
        P("Parameter", styles["TableHeader"]),
        P("Code", styles["TableHeader"]),
        P("Observed Value", styles["TableHeader"]),
        P("Unit", styles["TableHeader"]),
    ]]

    for observation in observations:
        parameter = first_present(observation.get("parameter"), observation.get("parameter_name"), observation.get("name"), observation.get("field"), default="Not recorded")
        code = first_present(observation.get("parameter_code"), observation.get("code"), default="")
        value = first_present(observation.get("value_numeric"), observation.get("value_text"), observation.get("value"), observation.get("observed_value"), default="Not recorded")
        unit = observation.get("unit") or ""
        rows.append([
            P(parameter, styles["TableCell"]),
            P(code, styles["TableCellCenter"]),
            P(format_value(value), styles["TableCellCenter"]),
            P(unit, styles["TableCellCenter"]),
        ])

    elements.append(make_table(rows, col_widths=[63 * mm, 27 * mm, 49 * mm, 31 * mm], header=True, alignments=["LEFT", "CENTER", "CENTER", "CENTER"]))
    return elements


def build_calculations(calculations, styles):
    elements = [Paragraph("Calculations", styles["SubHeading"])]
    if not calculations:
        elements.append(Paragraph("No calculations recorded.", styles["BodySmall"]))
        return elements

    rows = [[
        P("Calculation", styles["TableHeader"]),
        P("Calculated Value", styles["TableHeader"]),
        P("Unit", styles["TableHeader"]),
        P("Formula", styles["TableHeader"]),
    ]]

    for calculation in calculations:
        name = first_present(calculation.get("calculation"), calculation.get("calculation_name"), calculation.get("name"), calculation.get("calculation_type"), default="Not recorded")
        value = first_present(calculation.get("calculated_value"), calculation.get("value"), default="Not recorded")
        unit = calculation.get("unit") or ""
        formula = first_present(calculation.get("formula"), calculation.get("calculation_type"), default="Not specified")
        rows.append([
            P(name, styles["TableCell"]),
            P(format_value(value), styles["TableCellCenter"]),
            P(unit, styles["TableCellCenter"]),
            P(formula, styles["TableCell"]),
        ])

    elements.append(make_table(rows, col_widths=[45 * mm, 37 * mm, 24 * mm, 64 * mm], header=True, alignments=["LEFT", "CENTER", "CENTER", "LEFT"]))
    return elements


def build_evaluation(test, detailed_result, styles):
    requirement = first_present(
        test.get("requirement"),
        test.get("acceptance_condition"),
        detailed_result.get("acceptance_condition"),
        default="Not specified",
    )
    mpe = first_present(test.get("mpe"), test.get("mpe_value"), detailed_result.get("mpe_value"), default="Not recorded")
    measured = detailed_result.get("measured_value")
    error = first_present(detailed_result.get("error_value"), detailed_result.get("corrected_error"))
    corrected_error = detailed_result.get("corrected_error")
    acceptance = first_present(detailed_result.get("acceptance_condition"), test.get("acceptance_condition"), default="Not specified")
    result = first_present(detailed_result.get("pass_fail"), test.get("result"), default="Not recorded")
    summary = first_present(detailed_result.get("result_summary"), test.get("result_summary"), default="")

    rows = [[
        P("Requirement / MPE", styles["TableHeader"]),
        P("Measured", styles["TableHeader"]),
        P("Error", styles["TableHeader"]),
        P("Corrected Error", styles["TableHeader"]),
        P("Result", styles["TableHeader"]),
    ], [
        P(f"{safe(requirement)} | MPE: {format_value(mpe)}", styles["TableCell"]),
        P(format_value(measured), styles["TableCellCenter"]),
        P(format_value(error), styles["TableCellCenter"]),
        P(format_value(corrected_error), styles["TableCellCenter"]),
        Paragraph(safe(result), styles[result_style_name(safe(result), styles)]),
    ]]

    table = make_table(rows, col_widths=[69 * mm, 24 * mm, 22 * mm, 27 * mm, 28 * mm], header=True, alignments=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"])
    elements = [Paragraph("Evaluation", styles["SubHeading"]), table]
    elements.append(Spacer(1, 2))
    elements.append(
        make_key_value_table(
            [
                ("Acceptance Condition", acceptance),
                ("Result Summary", summary or "Not recorded"),
            ],
            styles,
            col_widths=[41 * mm, 129 * mm],
        )
    )

    calc_version = first_present(detailed_result.get("calculation_version"), test.get("calculation_version"))
    ruleset_version = test.get("ruleset_version")
    if calc_version or ruleset_version:
        elements.append(Spacer(1, 2))
        elements.append(
            Paragraph(
                f"Calculation version: {safe(calc_version, 'Not recorded')} | Ruleset version: {safe(ruleset_version, 'Not recorded')}",
                styles["BodySmall"],
            )
        )

    remarks = test.get("remarks")
    if remarks:
        elements.append(Paragraph(f"<b>Remarks:</b> {safe(remarks)}", styles["BodySmall"]))

    return elements


def build_test_block(test, index, styles):
    test_name = first_present(
        test.get("test_name"),
        test.get("test_code"),
        test.get("name"),
        test.get("test_definition_name"),
        default=f"Test {index}",
    )
    test_code = first_present(test.get("test_code"), test.get("code"), default="Not recorded")
    category = first_present(test.get("category"), test.get("test_category"), default="")
    clause = first_present(test.get("reference_clause"), test.get("clause"), default="Not specified")
    applicability = get_applicability(test)
    procedure = first_present(test.get("procedure"), default="Not specified")
    result = get_test_result(test)

    block = [
        Paragraph(f"Test {index} - {safe(test_name)} ({safe(test_code)})", styles["TestHeading"]),
    ]

    meta_rows = [
        [P("Test Code", styles["TableCellBold"]), P(test_code, styles["TableCell"]),
         P("Reference Clause", styles["TableCellBold"]), P(clause, styles["TableCell"])],
        [P("Applicability", styles["TableCellBold"]), P(applicability, styles["TableCell"]),
         P("Category", styles["TableCellBold"]), P(category, styles["TableCell"])],
        [P("Procedure", styles["TableCellBold"]), P(procedure, styles["TableCell"]),
         P("Stored Result", styles["TableCellBold"]), Paragraph(safe(result), styles[result_style_name(safe(result), styles)])],
    ]
    meta = make_table(meta_rows, col_widths=[25 * mm, 60 * mm, 31 * mm, 54 * mm], header=False, row_background=False)
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BURGUNDY_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), BURGUNDY_LIGHT),
    ]))
    block.extend([meta, Spacer(1, 2)])

    if str(result).upper() in {"N/A", "NA", "NOT APPLICABLE"} or str(applicability).upper() in {"NOT_APPLICABLE", "N/A", "NOT APPLICABLE"}:
        block.append(
            make_key_value_table(
                [
                    ("Applicability", "Not Applicable"),
                    ("N/A Reason", test.get("na_reason") or "No reason recorded"),
                    ("Result", "N/A"),
                    ("Remarks", test.get("remarks") or ""),
                ],
                styles,
                col_widths=[41 * mm, 129 * mm],
            )
        )
        return KeepTogether(block)

    detailed_result = get_detailed_result(test)
    block.extend(build_observations(test.get("observations") or [], styles))
    block.append(Spacer(1, 2))
    block.extend(build_calculations(test.get("calculations") or [], styles))
    block.append(Spacer(1, 2))
    block.extend(build_evaluation(test, detailed_result, styles))

    return KeepTogether(block)


# ============================================================
# SECTION 7 - DETAILED TEST RESULTS
# ============================================================

def build_test_results(data, styles):
    tests = data.get("tests") or []
    elements = [Paragraph("7. Detailed Test Results", styles["SectionHeading"])]

    if not tests:
        elements.append(Paragraph("No tests recorded.", styles["BodySmall"]))
    else:
        for index, test in enumerate(tests, start=1):
            elements.append(build_test_block(test, index, styles))
            if index < len(tests):
                elements.append(Spacer(1, 4))

    construction = data.get("construction_examination") or []
    if construction:
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("Construction Examination (Non-Numerical)", styles["SubHeading"]))
        rows = [[P("Examination Item", styles["TableHeader"]), P("Status", styles["TableHeader"]), P("Remarks", styles["TableHeader"])]]
        for item in construction:
            status = item.get("status") or item.get("result") or "Not recorded"
            rows.append([
                P(item.get("item") or item.get("name"), styles["TableCell"]),
                Paragraph(safe(status), styles[result_style_name(safe(status), styles)]),
                P(item.get("remarks"), styles["TableCell"]),
            ])
        elements.append(make_table(rows, col_widths=[55 * mm, 25 * mm, 90 * mm], header=True, alignments=["LEFT", "CENTER", "LEFT"]))

    return elements


# ============================================================
# SECTION 8 - OVERALL EVALUATION
# ============================================================

def build_conclusion(data, styles):
    session = data.get("test_session") or {}
    report = data.get("report") or {}
    instrument = data.get("instrument") or {}
    standard = data.get("standard") or {}
    overall = first_present(report.get("overall_result"), session.get("overall_result"), data.get("overall_result"), default="Not recorded")

    result_box = Table(
        [[
            P("OVERALL RESULT", styles["TableCellBold"]),
            Paragraph(safe(overall), styles[result_style_name(safe(overall), styles)]),
        ]],
        colWidths=[45 * mm, 125 * mm],
    )
    result_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.65, BURGUNDY),
        ("BACKGROUND", (0, 0), (0, 0), BURGUNDY_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    manufacturer = instrument.get("manufacturer") or "the manufacturer"
    model = instrument.get("model") or "the instrument"
    designation = instrument.get("type_designation") or ""
    standard_name = first_present(standard.get("standard_code"), standard.get("title"), default="the applicable standard")

    narrative = (
        f"The test record presented in this report covers the recorded evaluation of "
        f"{manufacturer} {model} {designation}. The recorded results are assessed "
        f"against {standard_name}. The conclusion shown above reflects the stored "
        f"session/report result and does not independently recalculate measurement rules."
    )

    remarks = first_present(report.get("remarks"), session.get("remarks"), data.get("remarks"), default="")
    return [
        Paragraph("8. Overall Evaluation / Conclusion", styles["SectionHeading"]),
        result_box,
        Spacer(1, 4),
        Paragraph(narrative, styles["BodySmall"]),
        Spacer(1, 3),
        Paragraph(f"<b>Remarks:</b> {safe(remarks)}", styles["BodySmall"]),
    ]


# ============================================================
# SECTION 9 - REMARKS / NON-CONFORMITIES
# ============================================================

def build_remarks(data, styles):
    report = data.get("report") or {}
    session = data.get("test_session") or {}
    general = first_present(report.get("remarks"), session.get("remarks"), data.get("remarks"), default="No general remarks recorded.")
    non_conformities = data.get("non_conformities") or []

    nc_text = "None recorded." if not non_conformities else "; ".join(
        safe(item.get("description") if isinstance(item, dict) else item, "Not specified")
        for item in non_conformities
    )

    return [
        Paragraph("9. Remarks / Non-Conformities", styles["SectionHeading"]),
        make_key_value_table(
            [("General Remarks", general), ("Non-Conformities", nc_text)],
            styles,
        ),
    ]


# ============================================================
# SECTION 10 - REVIEW / APPROVAL
# ============================================================

def build_approval(data, styles):
    report = data.get("report") or {}
    reviewer = report.get("reviewer") or {}
    reviewer_name = get_reviewer_name(report)
    reviewer_designation = first_present(reviewer.get("designation"), report.get("reviewer_designation"), default="Not recorded")
    status = first_present(report.get("report_status"), report.get("status"), default="GENERATED")
    generated_on = first_present(report.get("generated_at"), report.get("report_date"))
    generated_by = first_present(report.get("generated_by"), "NAWI Test & Compliance System")
    approved_at = first_present(report.get("approved_at"), report.get("approval_date"))
    signature_status = "APPROVED" if str(status).upper() == "APPROVED" else "PENDING APPROVAL"

    rows = [
        ("Report Status", status),
        ("Reviewer", reviewer_name),
        ("Reviewer Designation", reviewer_designation),
        ("Generated On", display_timestamp(generated_on)),
        ("Generated By", generated_by),
        ("Approval Date", display_timestamp(approved_at)),
        ("Signature Status", signature_status),
        ("Signed At", display_timestamp(approved_at) if approved_at else "Not recorded"),
        ("Report Hash", report.get("report_hash") or report.get("hash")),
    ]

    approval_table = make_key_value_table(rows, styles)
    signature_table = Table(
        [[
            Paragraph("Reviewer / Approving Authority", styles["TableCellBold"]),
            Paragraph("Signature / Seal", styles["TableCellBold"]),
        ], [
            Paragraph(f"Name: {safe(reviewer_name)}<br/><br/>Date: {format_datetime(approved_at, False) if approved_at else 'Not recorded'}", styles["TableCell"]),
            Paragraph("<br/><br/>____________________________", styles["TableCell"]),
        ]],
        colWidths=[85 * mm, 85 * mm],
    )
    signature_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), BURGUNDY_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [Paragraph("10. Review / Approval", styles["SectionHeading"]), approval_table, Spacer(1, 4), signature_table]


# ============================================================
# SECTION 11 - SYNTHETIC NOTICE
# ============================================================

def build_synthetic_notice(data, styles):
    notice_text = (
        "Where this prototype is demonstrated with synthetic or sample values, those values are for "
        "software demonstration and report-format verification only. They are not actual laboratory "
        "measurements, calibration records, or legal-metrology evidence. Production reports should be "
        "generated only from the approved structured test data recorded by the laboratory system."
    )

    notice = Table([[Paragraph(notice_text, styles["Notice"])]], colWidths=[170 * mm])
    notice.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [Paragraph("11. Synthetic Demonstration Data Notice", styles["SectionHeading"]), notice]


# ============================================================
# SECTION 12 - ATTACHMENTS
# ============================================================

def build_attachments(data, styles):
    attachments = data.get("attachments") or []
    rows = [[P("ID", styles["TableHeader"]), P("File", styles["TableHeader"]), P("Type", styles["TableHeader"]), P("Description", styles["TableHeader"])]]

    if attachments:
        for index, item in enumerate(attachments, start=1):
            rows.append([
                P(item.get("attachment_id") or index, styles["TableCellCenter"]),
                P(item.get("file_name") or item.get("filename"), styles["TableCell"]),
                P(item.get("attachment_type") or item.get("type"), styles["TableCell"]),
                P(item.get("description"), styles["TableCell"]),
            ])
    else:
        rows.append([P("", styles["TableCell"]), P("No attachments recorded.", styles["TableCell"]), P("", styles["TableCell"]), P("", styles["TableCell"])])

    table = make_table(rows, col_widths=[15 * mm, 58 * mm, 37 * mm, 60 * mm], header=True, alignments=["CENTER", "LEFT", "LEFT", "LEFT"])
    return [Paragraph("12. Attachments", styles["SectionHeading"]), table]


# ============================================================
# MAIN PDF CREATOR
# ============================================================

def create_pdf(data: dict, output_path: str = "NAWI_Test_Report.pdf"):
    """Generate a formal NAWI PDF report from structured report data."""
    if not isinstance(data, dict):
        raise TypeError("Report data must be a dictionary.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="NAWI Test Report",
        author="NAWI Report Generation System",
        subject="Non-Automatic Weighing Instrument Test Report",
    )
    document.report_data = data

    story = []

    # PAGE 1: IDENTIFICATION
    story.extend(build_report_header(data, styles))
    story.append(Spacer(1, 5))
    story.extend(build_laboratory_information(data, styles))
    story.append(Spacer(1, 4))
    story.extend(build_instrument_information(data, styles))
    story.append(Spacer(1, 4))
    story.extend(build_session_information(data, styles))

    # PAGE 2: EQUIPMENT + ENVIRONMENT + SUMMARY
    story.append(PageBreak())
    story.extend(build_test_equipment(data, styles))
    story.append(Spacer(1, 4))
    story.extend(build_environmental_conditions(data, styles))
    story.append(Spacer(1, 4))
    story.extend(build_test_summary(data, styles))

    # PAGE 3+: DETAILED TESTS
    story.append(PageBreak())
    story.extend(build_test_results(data, styles))

    # FINAL PAGE: CONCLUSION / APPROVAL / NOTICE / ATTACHMENTS
    story.append(PageBreak())
    story.extend(build_conclusion(data, styles))
    story.append(Spacer(1, 6))
    story.extend(build_remarks(data, styles))
    story.append(Spacer(1, 5))
    story.extend(build_approval(data, styles))
    story.append(Spacer(1, 5))
    story.extend(build_synthetic_notice(data, styles))
    story.append(Spacer(1, 5))
    story.extend(build_attachments(data, styles))

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
    try:
        try:
            from .sample_report_data import SAMPLE_REPORT_DATA
        except ImportError:
            from .sample_report_data import sample_report_data as SAMPLE_REPORT_DATA

        output = create_pdf(SAMPLE_REPORT_DATA, output_path="NAWI_Test_Report.pdf")
        print("PDF generated successfully:")
        print(output)
    except ImportError as error:
        print("Could not import sample report data.")
        print(error)
