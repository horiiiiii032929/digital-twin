from src.digital_twin.onboarding_workflow import OnboardingSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, OnboardingSession] = {}

    def save(self, session: OnboardingSession) -> OnboardingSession:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> OnboardingSession | None:
        return self._sessions.get(session_id)

    def clear(self) -> None:
        self._sessions.clear()


store = SessionStore()
