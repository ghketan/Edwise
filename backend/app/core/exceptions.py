from fastapi import HTTPException, status


class EdwiseException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(EdwiseException):
    def __init__(self, detail: str = "Resource not found or out of scope"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ForbiddenError(EdwiseException):
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthorizedError(EdwiseException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ConflictError(EdwiseException):
    def __init__(self, detail: str = "Resource conflict or state mismatch"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(EdwiseException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=422, detail=detail)
