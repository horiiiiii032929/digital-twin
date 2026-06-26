from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.api.app.store import store
from src.digital_twin.onboarding_workflow import create_session, submit_message
from src.digital_twin.tutor_policy import FieldStatus


class MessageRequest(BaseModel):
    content: str


class PolicyFieldUpdateRequest(BaseModel):
    value: str | list[str]
    status: FieldStatus = FieldStatus.RESOLVED


app = FastAPI(title="Digital Twin Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "session_not_found",
            "message": "Onboarding session was not found.",
        },
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/onboarding/sessions", status_code=status.HTTP_201_CREATED)
def create_onboarding_session():
    session = create_session()
    return store.save(session)


@app.get("/api/onboarding/sessions/{session_id}")
def get_onboarding_session(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    return session


@app.post("/api/onboarding/sessions/{session_id}/messages")
def submit_onboarding_message(session_id: str, request: MessageRequest):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    updated = submit_message(session, request.content)
    return store.save(updated)


@app.patch("/api/onboarding/sessions/{session_id}/policy-fields/{field_id}")
def update_policy_field(
    session_id: str,
    field_id: str,
    request: PolicyFieldUpdateRequest,
):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    if session.policy is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "policy_not_ready",
                "message": "Complete the interview before editing policy fields.",
            },
        )

    for field in session.policy.all_fields:
        if field.id == field_id:
            field.value = request.value
            field.status = request.status
            return store.save(session)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "policy_field_not_found",
            "message": "Policy field was not found.",
        },
    )
