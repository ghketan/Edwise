from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import (
    check_teacher_class_scope,
    get_current_user,
    get_db,
    require_teacher_or_admin,
)
from backend.app.models.institution import Class, Enrollment
from backend.app.models.user import User, UserRole
from backend.app.schemas.academics import AnnouncementCreate, AnnouncementResponse
from backend.app.services.academics_service import (
    create_announcement,
    delete_announcement,
    get_announcements,
)

router = APIRouter(prefix="/announcements", tags=["Notice Board & Announcements"])


@router.post("", response_model=AnnouncementResponse)
def api_create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Teacher or Administrator creates a class broadcast notice.
    """
    if current_user.role == UserRole.TEACHER and payload.class_id is not None:
        check_teacher_class_scope(
            db=db,
            user=current_user,
            class_id=payload.class_id,
            session_id=payload.session_id,
            section_id=payload.section_id
        )

    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    ann = create_announcement(
        db=db,
        teacher_id=teacher_id,
        session_id=payload.session_id,
        title=payload.title,
        content=payload.content,
        class_id=payload.class_id,
        section_id=payload.section_id,
        priority=payload.priority
    )

    class_name = "All Classes"
    if ann.class_id:
        cls_obj = db.query(Class).filter(Class.id == ann.class_id).first()
        class_name = cls_obj.name if cls_obj else f"Class #{ann.class_id}"

    return AnnouncementResponse(
        id=ann.id,
        session_id=ann.session_id,
        class_id=ann.class_id,
        section_id=ann.section_id,
        teacher_id=ann.teacher_id,
        title=ann.title,
        content=ann.content,
        priority=ann.priority,
        created_at=ann.created_at,
        teacher_name=current_user.teacher_profile.full_name if current_user.teacher_profile else "Administration",
        class_name=class_name
    )


@router.get("", response_model=List[AnnouncementResponse])
def api_get_announcements(
    session_id: int,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List announcements:
    - Students see announcements targeted to their enrolled class or All Classes.
    - Teachers and Admins can filter by class or view all.
    """
    target_class_id = class_id
    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            return []
        st = current_user.student_profile
        enr = db.query(Enrollment).filter(
            Enrollment.student_id == st.id,
            Enrollment.session_id == session_id
        ).first()
        target_class_id = enr.class_id if enr else st.class_id

    announcements = get_announcements(
        db=db,
        session_id=session_id,
        class_id=target_class_id
    )

    res = []
    for ann in announcements:
        class_name = "All Classes"
        if ann.class_id:
            cls_obj = db.query(Class).filter(Class.id == ann.class_id).first()
            class_name = cls_obj.name if cls_obj else f"Class #{ann.class_id}"

        res.append(AnnouncementResponse(
            id=ann.id,
            session_id=ann.session_id,
            class_id=ann.class_id,
            section_id=ann.section_id,
            teacher_id=ann.teacher_id,
            title=ann.title,
            content=ann.content,
            priority=ann.priority,
            created_at=ann.created_at,
            teacher_name=ann.teacher.full_name if ann.teacher else "Administration",
            class_name=class_name
        ))
    return res


@router.delete("/{announcement_id}")
def api_delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Delete an announcement. Only the creator teacher or Administrator can delete.
    """
    teacher_id = current_user.teacher_profile.id if current_user.teacher_profile else None
    is_admin = current_user.role == UserRole.ADMINISTRATOR
    delete_announcement(
        db=db,
        announcement_id=announcement_id,
        teacher_id=teacher_id,
        is_admin=is_admin
    )
    return {"status": "success", "message": "Announcement deleted successfully"}
