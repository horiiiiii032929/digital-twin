from typing import Protocol

from src.digital_twin.onboarding.models import OnboardingSession


class SessionRepository(Protocol):
    def get(self, session_id: str) -> OnboardingSession | None: ...

    def save(self, session: OnboardingSession) -> OnboardingSession: ...

    def clear(self) -> None: ...


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, OnboardingSession] = {}

    def get(self, session_id: str) -> OnboardingSession | None:
        session = self._sessions.get(session_id)
        return session.model_copy(deep=True) if session is not None else None

    def save(self, session: OnboardingSession) -> OnboardingSession:
        stored = session.model_copy(deep=True)
        self._sessions[stored.session_id] = stored
        return stored.model_copy(deep=True)

    def clear(self) -> None:
        self._sessions.clear()
