from src.digital_twin.onboarding import InMemorySessionRepository


class SessionStore(InMemorySessionRepository):
    """Compatibility alias for the default in-memory repository."""


store = SessionStore()
