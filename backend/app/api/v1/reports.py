from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_student_scope,
    check_teacher_class_scope,
    get_current_user,
    get_db,
    require_teacher_or_admin,
)
from backend.app.models.user import User
from backend.app.services.audit_service import create_audit_entry
from backend.app.services.report_service import (
    generate_class_report_excel,
    generate_student_report_excel,
    generate_student_report_pdf,
)

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])


@router.get("/student/{student_id}/pdf")
def api_student_report_pdf(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-013, UI-007, C-02, M-06: Export student progress report in PDF format.
    Students can only download their own report.
    Teachers can only download reports for their assigned students.
    Audited on export (M-06).
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    pdf_buffer = generate_student_report_pdf(
        db=db,
        student_id=student_id,
        session_id=session_id,
        requester_role=current_user.role.value
    )
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="report.exported_pdf",
        entity_name="student_report",
        entity_id=student_id,
        new_values={"session_id": session_id, "format": "pdf"},
        reason="User downloaded student PDF report"
    )
    db.commit()

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=student_{student_id}_report.pdf"}
    )


@router.get("/student/{student_id}/excel")
def api_student_report_excel(
    student_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    R-013, UI-007, C-02, M-06: Export student progress report in Excel format.
    """
    check_student_scope(db=db, user=current_user, student_id=student_id, session_id=session_id)
    excel_buffer = generate_student_report_excel(
        db=db,
        student_id=student_id,
        session_id=session_id,
        requester_role=current_user.role.value
    )
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="report.exported_excel",
        entity_name="student_report",
        entity_id=student_id,
        new_values={"session_id": session_id, "format": "excel"},
        reason="User downloaded student Excel report"
    )
    db.commit()

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=student_{student_id}_report.xlsx"}
    )


@router.get("/class/{class_id}/excel")
def api_class_report_excel(
    class_id: int,
    session_id: int,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    R-013, UI-007, C-02, M-06: Export class performance summary in Excel format.
    Enforces teacher class scope.
    """
    check_teacher_class_scope(
        db=db,
        user=current_user,
        class_id=class_id,
        session_id=session_id,
        section_id=section_id
    )
    excel_buffer = generate_class_report_excel(
        db=db,
        class_id=class_id,
        session_id=session_id,
        section_id=section_id,
        requester_role=current_user.role.value
    )
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="class_report.exported_excel",
        entity_name="class_report",
        entity_id=class_id,
        new_values={"session_id": session_id, "section_id": section_id, "format": "excel"},
        reason="Teacher or Admin exported class summary report"
    )
    db.commit()

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=class_{class_id}_summary.xlsx"}
    )
