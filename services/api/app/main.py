from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.api.app.store import store
from src.digital_twin.onboarding_workflow import (
    add_custom_preview_case,
    add_source_inventory_item,
    confirm_revision_proposal,
    create_session,
    discard_revision_proposal,
    set_preview_decision,
    submit_message,
    update_approval_checklist_item,
    update_policy_field_value,
    update_source_inventory_item,
)
from src.digital_twin.tutor_policy import (
    FieldStatus,
    PreviewDecisionValue,
    PromptTag,
    SourceLabel,
    SourcePermissionStatus,
)


class MessageRequest(BaseModel):
    content: str


class PolicyFieldUpdateRequest(BaseModel):
    value: str | list[str] | dict
    status: FieldStatus = FieldStatus.RESOLVED


class SourceInventoryCreateRequest(BaseModel):
    name: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED
    excluded: bool = False
    sensitive: bool | None = None
    notes: str = ""


class SourceInventoryUpdateRequest(BaseModel):
    name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    permission_status: SourcePermissionStatus | None = None
    source_label: SourceLabel | None = None
    excluded: bool | None = None
    sensitive: bool | None = None
    notes: str | None = None


class ApprovalChecklistUpdateRequest(BaseModel):
    checked: bool


class PreviewDecisionRequest(BaseModel):
    decision: PreviewDecisionValue
    reason: str | None = None


class CustomPreviewRequest(BaseModel):
    prompt: str
    tag: PromptTag


app = FastAPI(title="Digital Twin Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
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

    try:
        return store.save(
            update_policy_field_value(
                session,
                field_id,
                request.value,
                request.status,
            )
        )
    except ValueError as exc:
        if str(exc) == "policy_field_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "policy_field_not_found",
                    "message": "Policy field was not found.",
                },
            ) from exc
        raise


@app.post("/api/onboarding/sessions/{session_id}/source-inventory")
def create_source_inventory_item(
    session_id: str,
    request: SourceInventoryCreateRequest,
):
    session = _get_session_or_404(session_id)
    return store.save(
        add_source_inventory_item(
            session,
            name=request.name,
            mime_type=request.mime_type,
            size_bytes=request.size_bytes,
            permission_status=request.permission_status,
            source_label=request.source_label,
            excluded=request.excluded,
            sensitive=request.sensitive,
            notes=request.notes,
        )
    )


@app.patch("/api/onboarding/sessions/{session_id}/source-inventory/{source_id}")
def patch_source_inventory_item(
    session_id: str,
    source_id: str,
    request: SourceInventoryUpdateRequest,
):
    session = _get_session_or_404(session_id)
    try:
        return store.save(
            update_source_inventory_item(
                session,
                source_id,
                **request.model_dump(exclude_unset=True),
            )
        )
    except ValueError as exc:
        if str(exc) == "source_inventory_item_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "source_inventory_item_not_found",
                    "message": "Source inventory item was not found.",
                },
            ) from exc
        raise


@app.patch("/api/onboarding/sessions/{session_id}/approval-checklist/{item_id}")
def patch_approval_checklist_item(
    session_id: str,
    item_id: str,
    request: ApprovalChecklistUpdateRequest,
):
    session = _get_session_or_404(session_id)
    try:
        return store.save(update_approval_checklist_item(session, item_id, request.checked))
    except ValueError as exc:
        if str(exc) == "approval_item_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "approval_item_not_found",
                    "message": "Approval checklist item was not found.",
                },
            ) from exc
        raise


@app.patch(
    "/api/onboarding/sessions/{session_id}/preview-cases/{preview_case_id}/decision"
)
def patch_preview_decision(
    session_id: str,
    preview_case_id: str,
    request: PreviewDecisionRequest,
):
    session = _get_session_or_404(session_id)
    try:
        return store.save(
            set_preview_decision(
                session,
                preview_case_id,
                request.decision,
                request.reason,
            )
        )
    except ValueError as exc:
        if str(exc) == "preview_case_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "preview_case_not_found",
                    "message": "Preview case was not found.",
                },
            ) from exc
        raise


@app.post("/api/onboarding/sessions/{session_id}/preview-cases")
def create_custom_preview_case(
    session_id: str,
    request: CustomPreviewRequest,
):
    session = _get_session_or_404(session_id)
    try:
        return store.save(
            add_custom_preview_case(
                session,
                prompt=request.prompt,
                tag=request.tag,
            )
        )
    except ValueError as exc:
        if str(exc) == "policy_not_ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "policy_not_ready",
                    "message": "Complete the interview before creating previews.",
                },
            ) from exc
        raise


@app.post("/api/onboarding/sessions/{session_id}/revision-proposal/confirm")
def confirm_revision(session_id: str):
    session = _get_session_or_404(session_id)
    try:
        return store.save(confirm_revision_proposal(session))
    except ValueError as exc:
        if str(exc) == "revision_proposal_not_found":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "revision_proposal_not_found",
                    "message": "There is no pending revision proposal.",
                },
            ) from exc
        raise


@app.post("/api/onboarding/sessions/{session_id}/revision-proposal/discard")
def discard_revision(session_id: str):
    session = _get_session_or_404(session_id)
    try:
        return store.save(discard_revision_proposal(session))
    except ValueError as exc:
        if str(exc) == "revision_proposal_not_found":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "revision_proposal_not_found",
                    "message": "There is no pending revision proposal.",
                },
            ) from exc
        raise


def _get_session_or_404(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    return session
