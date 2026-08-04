from pathlib import Path

from src.digital_twin.onboarding import InMemorySessionRepository
from src.digital_twin.student import SQLiteStudentRepository


class SessionStore(InMemorySessionRepository):
    """Compatibility alias for the default in-memory repository."""


store = SessionStore()
student_store = SQLiteStudentRepository(
    Path(__file__).resolve().parents[3]
    / "data/interim/student-workflow/student-workflow.sqlite3"
)
