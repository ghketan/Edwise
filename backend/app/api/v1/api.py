from fastapi import APIRouter
from backend.app.api.v1 import (
    analytics,
    announcements,
    assignments,
    attendance,
    audit,
    auth,
    doubts,
    exams,
    institution,
    marks,
    ml,
    recommendations,
    reports,
    students,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(institution.router)
api_router.include_router(attendance.router)
api_router.include_router(exams.router)
api_router.include_router(marks.router)
api_router.include_router(assignments.router)
api_router.include_router(announcements.router)
api_router.include_router(doubts.router)
api_router.include_router(analytics.router)
api_router.include_router(ml.router)
api_router.include_router(students.router)
api_router.include_router(recommendations.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)

