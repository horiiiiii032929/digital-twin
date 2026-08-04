"""FastAPI route modules."""
from services.api.app.routers.onboarding import router as onboarding_router
from services.api.app.routers.student import router as student_router


__all__ = ["onboarding_router", "student_router"]
