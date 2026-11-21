from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, require_admin
from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.core.security import get_password_hash
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserResponse, UserUpdate
from backend.app.services.audit_service import create_audit_entry

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).all()


@router.post("", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise ConflictError(f"User with username '{user_in.username}' already exists")

    if user_in.email:
        email_exists = db.query(User).filter(User.email == str(user_in.email)).first()
        if email_exists:
            raise ConflictError(f"Email '{user_in.email}' is already in use")

    try:
        hashed_pwd = get_password_hash(user_in.password)
    except ValueError as e:
        raise ValidationError(str(e))

    user = User(
        username=user_in.username,
        email=str(user_in.email) if user_in.email else None,
        hashed_password=hashed_pwd,
        role=user_in.role,
        is_active=user_in.is_active,
        is_verified=user_in.is_verified
    )
    db.add(user)
    db.flush()

    create_audit_entry(
        db=db,
        user_id=admin.id,
        action="user.created",
        entity_name="user",
        entity_id=user.id,
        new_values={"username": user.username, "role": user.role.value, "is_active": user.is_active},
        reason="Admin created user account"
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")

    old_vals = {"email": user.email, "is_active": user.is_active, "is_verified": user.is_verified}

    if user_in.email is not None:
        email_str = str(user_in.email)
        existing_email = db.query(User).filter(User.email == email_str, User.id != user_id).first()
        if existing_email:
            raise ConflictError(f"Email '{email_str}' is already in use by another user")
        user.email = email_str

    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.is_verified is not None:
        user.is_verified = user_in.is_verified
    if user_in.password:
        try:
            user.hashed_password = get_password_hash(user_in.password)
        except ValueError as e:
            raise ValidationError(str(e))

    db.flush()
    create_audit_entry(
        db=db,
        user_id=admin.id,
        action="user.updated",
        entity_name="user",
        entity_id=user.id,
        old_values=old_vals,
        new_values={"email": user.email, "is_active": user.is_active, "is_verified": user.is_verified},
        reason="Admin updated user account"
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/verify", response_model=UserResponse)
def verify_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")

    old_val = user.is_verified
    user.is_verified = True
    db.flush()

    create_audit_entry(
        db=db,
        user_id=admin.id,
        action="user.verified",
        entity_name="user",
        entity_id=user.id,
        old_values={"is_verified": old_val},
        new_values={"is_verified": True},
        reason="Admin verified user account"
    )
    db.commit()
    db.refresh(user)
    return user
