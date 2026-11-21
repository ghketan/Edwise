from typing import Optional
from pydantic import BaseModel


class ReportExportRequest(BaseModel):
    session_id: int
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    student_id: Optional[int] = None
    subject_id: Optional[int] = None
    format: str = "pdf"  # "pdf" or "excel"

