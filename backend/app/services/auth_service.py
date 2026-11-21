from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.app.models.institution import Student, Teacher
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import StudentRegisterRequest, Token
from backend.app.services.audit_service import create_audit_entry
from backend.app.core.logging import logger

DUMMY_BCRYPT_HASH = "$2b$12$e8YkZ7kR74lXy9pUqT2K.O/Q0w5eXF6v1H1pZ7kR74lXy9pUqT2K."


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Verify username, password, and active+verified status (C-05, H-06).
    Timing-safe against user enumeration.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Dummy verification to equalize timing against enumeration
        verify_password(password, DUMMY_BCRYPT_HASH)
        return None

    if not verify_password(password, user.hashed_password):
        return None

    # Check active and verified status (C-05)
    if not user.is_active or not user.is_verified:
        return None

    return user


def create_user_tokens(db: Session, user: User) -> Token:
    """Generate access and refresh tokens for an authenticated user."""
    student_id = None
    teacher_id = None
    
    if user.role == UserRole.STUDENT and user.student_profile:
        student_id = user.student_profile.id
    elif user.role == UserRole.TEACHER and user.teacher_profile:
        teacher_id = user.teacher_profile.id

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "student_id": student_id,
        "teacher_id": teacher_id
    }
    
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username,
        student_id=student_id,
        teacher_id=teacher_id
    )


def register_student_account(
    db: Session,
    request: StudentRegisterRequest,
    client_ip: Optional[str] = None
) -> dict:
    """
    Contract API-002, R-003, T-006, C-04:
    Student self-registers with admission number and class.
    Always returns uniform 202 response to prevent admission number enumeration.
    Protected against race conditions, duplicate email 500s, and timing oracles.
    """
    # Uniform return value for all outcomes (C-04)
    uniform_response = {
        "message": "Registration request received and being processed.",
        "status": "pending_verification"
    }

    # Look for matching unclaimed roster entry
    student = db.query(Student).filter(
        Student.admission_number == request.admission_number,
        Student.class_id == request.class_id,
        Student.user_id.is_(None),
        Student.is_roster_claimed.is_(False)
    ).first()

    if not student:
        # Equalize bcrypt hash timing against enumeration
        try:
            get_password_hash("DummyTimingEqualizerPassword123")
        except Exception:
            pass
        logger.info(f"Student registration attempt unlinked or invalid for class_id={request.class_id}")
        return uniform_response

    # Check if user already exists
    existing_user = db.query(User).filter(User.username == request.admission_number).first()
    if existing_user:
        try:
            get_password_hash("DummyTimingEqualizerPassword123")
        except Exception:
            pass
        logger.info("Username collision during student registration")
        return uniform_response

    try:
        # Check email uniqueness before attempting insert
        if request.contact_email:
            email_str = str(request.contact_email)
            email_exists = db.query(User).filter(User.email == email_str).first()
            if email_exists:
                logger.info("Email already in use during student registration")
                return uniform_response

        hashed_pwd = get_password_hash(request.password)
        user = User(
            username=request.admission_number,
            email=str(request.contact_email) if request.contact_email else None,
            hashed_password=hashed_pwd,
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=True  # Verified against official unclaimed roster row
        )
        db.add(user)
        db.flush()

        # Link student record
        student.user_id = user.id
        student.is_roster_claimed = True
        if request.contact_email:
            student.contact_email = str(request.contact_email)
        if request.contact_phone:
            student.contact_phone = request.contact_phone

        # Record audit log in same transaction (R-014)
        create_audit_entry(
            db=db,
            user_id=user.id,
            action="student.registered",
            entity_name="student",
            entity_id=student.id,
            old_values={"is_roster_claimed": False, "user_id": None},
            new_values={"is_roster_claimed": True, "user_id": user.id},
            reason="Student roster claim and self-registration",
            ip_address=client_ip
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Database IntegrityError during student registration; rolled back safely")
        return uniform_response
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during student registration: {str(e)}")
        return uniform_response

    return uniform_response


def refresh_user_token(db: Session, refresh_token_str: str) -> Token:
    """Validate refresh token and issue new token pair enforcing active+verified (C-05)."""
    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        user_id = int(payload.get("sub"))
    except Exception as e:
        raise UnauthorizedError(f"Invalid refresh token: {str(e)}")

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active.is_(True),
        User.is_verified.is_(True)
    ).first()
    if not user:
        raise UnauthorizedError("User no longer exists, is inactive, or is unverified")

    return create_user_tokens(db, user)
