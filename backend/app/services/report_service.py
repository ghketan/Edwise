import io
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape as xml_escape
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session
from backend.app.core.exceptions import NotFoundError
from backend.app.models.academics import Exam, Mark
from backend.app.models.institution import AcademicSession, Class, Enrollment, Section, Student, Subject
from backend.app.services.analytics_service import get_attendance_analytics, get_student_vs_class_analytics


def sanitize_excel_cell(val: any) -> any:
    """Sanitize spreadsheet cell against formula injection (H-07)."""
    if isinstance(val, str) and len(val) > 0:
        if val[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val}"
    return val


def generate_student_report_pdf(
    db: Session,
    student_id: int,
    session_id: int,
    requester_role: Optional[str] = None
) -> io.BytesIO:
    """
    R-013, UI-007, H-07: Generates PDF Student Report Card using ReportLab.
    Safely escapes dynamic text against XML parsing crashes.
    Includes requester role and synthetic data banner.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    session_obj = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    session_name = session_obj.name if session_obj else "Academic Session"

    analytics = get_student_vs_class_analytics(db, student_id=student_id, session_id=session_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    elements = []

    # Header title
    title_style = ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1  # Center
    )
    elements.append(Paragraph("EDWISE LEARNING ANALYTICS PLATFORM", title_style))
    elements.append(Spacer(1, 4))

    subtitle_style = ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4b5563"),
        alignment=1
    )
    elements.append(Paragraph(f"Official Academic Progress Report — {xml_escape(session_name)}", subtitle_style))
    elements.append(Spacer(1, 12))

    # Synthetic data disclaimer banner (R-015, UI-007)
    if student.is_synthetic:
        banner_style = ParagraphStyle(
            name="BannerText",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#92400e"),
            alignment=1
        )
        banner_table = Table(
            [[Paragraph("<b>DEMO ARTIFACT:</b> This report contains synthetic demonstration data for evaluation purposes.", banner_style)]],
            colWidths=[540]
        )
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
            ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(banner_table)
        elements.append(Spacer(1, 14))

    # Student metadata table (with XML escaping H-07)
    s_name_esc = xml_escape(student.full_name)
    adm_no_esc = xml_escape(student.admission_number)
    role_info = f" | Requester Role: {xml_escape(requester_role)}" if requester_role else ""

    meta_data = [
        [
            Paragraph(f"<b>Student Name:</b> {s_name_esc}", styles["Normal"]),
            Paragraph(f"<b>Admission Number:</b> {adm_no_esc}", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Attendance Rate:</b> {analytics.attendance_rate}%", styles["Normal"]),
            Paragraph(f"<b>Overall Score:</b> {analytics.overall_percentage}%", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Generated On:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}{role_info}", styles["Normal"]),
            Paragraph(f"<b>Class Average:</b> {analytics.class_overall_average}%", styles["Normal"])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 16))

    # Exam performance table
    elements.append(Paragraph("<b>Assessment Record</b>", styles["Heading3"]))
    elements.append(Spacer(1, 6))

    table_data = [["Exam Name", "Subject", "Date", "Score", "Max Marks", "Percentage", "Class Avg"]]
    for ex in analytics.exams:
        score_str = "Absent" if ex.is_absent else (f"{ex.score:.1f}" if ex.score is not None else "Pending")
        pct_str = f"{ex.percentage:.1f}%" if ex.percentage is not None else "-"
        table_data.append([
            xml_escape(ex.exam_name),
            xml_escape(ex.subject_name),
            str(ex.date),
            score_str,
            f"{ex.max_marks:.0f}",
            pct_str,
            f"{ex.class_average:.1f}"
        ])

    if len(table_data) == 1:
        table_data.append(["No exams recorded", "-", "-", "-", "-", "-", "-"])

    exam_table = Table(table_data, colWidths=[110, 90, 70, 60, 65, 75, 70])
    exam_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(exam_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_student_report_excel(
    db: Session,
    student_id: int,
    session_id: int,
    requester_role: Optional[str] = None
) -> io.BytesIO:
    """
    R-013, UI-007, H-07, M-07: Generates Excel Student Report Card using openpyxl.
    Sanitizes against spreadsheet formula injection and includes synthetic data banner.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    session_obj = db.query(AcademicSession).filter(AcademicSession.id == session_id).first()
    session_name = session_obj.name if session_obj else "Academic Session"
    analytics = get_student_vs_class_analytics(db, student_id=student_id, session_id=session_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Progress Report"

    # Title styling
    ws.merge_cells("A1:G1")
    ws["A1"] = "EDWISE LEARNING ANALYTICS PLATFORM"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:G2")
    ws["A2"] = f"Academic Progress Report — {session_name}"
    ws["A2"].font = Font(name="Calibri", size=12, italic=True)
    ws["A2"].alignment = Alignment(horizontal="center")

    current_row = 3
    # Synthetic banner in Excel (M-07)
    if student.is_synthetic:
        ws.merge_cells(f"A{current_row}:G{current_row}")
        cell = ws[f"A{current_row}"]
        cell.value = "DEMO ARTIFACT: This report contains synthetic demonstration data for evaluation purposes."
        cell.font = Font(color="92400E", bold=True)
        cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
        current_row += 1

    current_row += 1
    # Metadata (with formula injection protection H-07)
    ws[f"A{current_row}"] = "Student Name:"
    ws[f"B{current_row}"] = sanitize_excel_cell(student.full_name)
    ws[f"D{current_row}"] = "Admission Number:"
    ws[f"E{current_row}"] = sanitize_excel_cell(student.admission_number)

    current_row += 1
    ws[f"A{current_row}"] = "Attendance Rate:"
    ws[f"B{current_row}"] = f"{analytics.attendance_rate}%"
    ws[f"D{current_row}"] = "Overall Percentage:"
    ws[f"E{current_row}"] = f"{analytics.overall_percentage}%"

    current_row += 1
    ws[f"A{current_row}"] = "Generated At:"
    ws[f"B{current_row}"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ws[f"D{current_row}"] = "Class Average:"
    ws[f"E{current_row}"] = f"{analytics.class_overall_average}%"

    for r in range(current_row - 2, current_row + 1):
        for col in ["A", "D"]:
            ws[f"{col}{r}"].font = Font(bold=True)

    current_row += 2
    # Exam Table Header
    headers = ["Exam Name", "Subject", "Date", "Score", "Max Marks", "Percentage", "Class Avg"]
    ws.append(headers)
    header_row = ws.max_row

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Exam Rows
    for ex in analytics.exams:
        score_val = "Absent" if ex.is_absent else (ex.score if ex.score is not None else "Pending")
        pct_val = f"{ex.percentage}%" if ex.percentage is not None else "-"
        ws.append([
            sanitize_excel_cell(ex.exam_name),
            sanitize_excel_cell(ex.subject_name),
            str(ex.date),
            score_val,
            ex.max_marks,
            pct_val,
            ex.class_average
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def generate_class_report_excel(
    db: Session,
    class_id: int,
    session_id: int,
    section_id: Optional[int] = None,
    requester_role: Optional[str] = None
) -> io.BytesIO:
    """
    R-013, UI-007, H-07, M-07: Generates Class Performance Summary Excel with formula protection and demo disclaimers.
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise NotFoundError("Class not found")

    enr_query = db.query(Enrollment).filter(
        Enrollment.class_id == class_id,
        Enrollment.session_id == session_id
    )
    if section_id:
        enr_query = enr_query.filter(Enrollment.section_id == section_id)

    enrollments = enr_query.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Class Performance Summary"

    ws.merge_cells("A1:F1")
    ws["A1"] = f"EDWISE CLASS SUMMARY — {sanitize_excel_cell(class_obj.name)}"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    ws["A1"].alignment = Alignment(horizontal="center")

    current_row = 2
    # Check if synthetic students exist
    has_synthetic = any(e.student and e.student.is_synthetic for e in enrollments)
    if has_synthetic:
        current_row += 1
        ws.merge_cells(f"A{current_row}:F{current_row}")
        cell = ws[f"A{current_row}"]
        cell.value = "DEMO ARTIFACT: This report contains synthetic demonstration data for evaluation purposes."
        cell.font = Font(color="92400E", bold=True)
        cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    current_row += 2
    headers = ["Roll No", "Admission No", "Student Name", "Attendance %", "Overall Score %", "Status"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col_idx)
        cell.value = header
        cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")

    for enr in enrollments:
        student = enr.student
        analytics = get_student_vs_class_analytics(db, student_id=student.id, session_id=session_id)
        ws.append([
            sanitize_excel_cell(enr.roll_number or "-"),
            sanitize_excel_cell(student.admission_number),
            sanitize_excel_cell(student.full_name),
            f"{analytics.attendance_rate}%",
            f"{analytics.overall_percentage}%",
            enr.status
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
