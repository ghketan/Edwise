from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, get_db
from backend.app.core.exceptions import UnauthorizedError
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    StudentRegisterRequest,
    StudentRegisterResponse,
    Token,
)
from backend.app.schemas.user import UserResponse
from backend.app.services.auth_service import (
    authenticate_user,
    create_user_tokens,
    refresh_user_token,
    register_student_account,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User authentication endpoint.
    H-06: Returns uniform 401 on all authentication failures (wrong password, inactive, unverified).
    """
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise UnauthorizedError("Invalid username or password")
    return create_user_tokens(db, user)


@router.post("/register-student", response_model=StudentRegisterResponse, status_code=202)
def register_student(
    request: StudentRegisterRequest,
    http_req: Request,
    db: Session = Depends(get_db)
):
    """
    Contract API-002: Student self-registers by matching an unclaimed roster record (R-003).
    C-04: Uniform 202 response prevents enumeration of admission numbers (T-006).
    """
    client_ip = http_req.client.host if http_req.client else None
    result = register_student_account(db, request, client_ip=client_ip)
    return StudentRegisterResponse(**result)


@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    return refresh_user_token(db, request.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
