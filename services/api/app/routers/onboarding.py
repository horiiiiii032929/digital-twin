from fastapi import APIRouter, HTTPException, status

from services.api.app.dependencies import SessionRepositoryDependency
from services.api.app.schemas import (
    ApprovalChecklistUpdateRequest,
    CustomPreviewRequest,
    MessageRequest,
    PolicyFieldUpdateRequest,
    PreviewDecisionRequest,
    SourceInventoryCreateRequest,
    SourceInventoryUpdateRequest,
)
from src.digital_twin.onboarding import (
    OnboardingSession,
    SessionRepository,
    SessionWriteConflictError,
)
from src.digital_twin.onboarding_workflow import (
    add_custom_preview_case,
    add_source_inventory_item,
    confirm_revision_proposal,
    create_session,
    create_supervisor_demo_session,
    discard_revision_proposal,
    set_preview_decision,
    submit_message,
    update_approval_checklist_item,
    update_policy_field_value,
    update_source_inventory_item,
)


router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "session_not_found",
            "message": "Onboarding session was not found.",
        },
    )


def _get_session_or_404(
    repository: SessionRepository,
    session_id: str,
) -> OnboardingSession:
    session = repository.get(session_id)
    if session is None:
        raise _not_found()
    return session


def _save_session(
    repository: SessionRepository,
    session: OnboardingSession,
) -> OnboardingSession:
    try:
        return repository.save(session)
    except (PermissionError, SessionWriteConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "session_write_conflict",
                "message": (
                    "This onboarding session changed in another request. "
                    "Reload it before applying the edit again."
                ),
            },
        ) from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/onboarding/sessions", status_code=status.HTTP_201_CREATED)
def create_onboarding_session(repository: SessionRepositoryDependency):
    return _save_session(repository, create_session())


@router.post(
    "/onboarding/sessions/supervisor-demo",
    status_code=status.HTTP_201_CREATED,
)
def create_synthetic_supervisor_demo_session(
    repository: SessionRepositoryDependency,
):
    """Return a populated local review state built only from synthetic metadata."""

    return _save_session(repository, create_supervisor_demo_session())


@router.get("/onboarding/sessions/{session_id}")
def get_onboarding_session(
    session_id: str,
    repository: SessionRepositoryDependency,
):
    return _get_session_or_404(repository, session_id)


@router.post("/onboarding/sessions/{session_id}/messages")
def submit_onboarding_message(
    session_id: str,
    request: MessageRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    return _save_session(repository, submit_message(session, request.content))


@router.patch("/onboarding/sessions/{session_id}/policy-fields/{field_id}")
def update_policy_field(
    session_id: str,
    field_id: str,
    request: PolicyFieldUpdateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    if session.policy is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "policy_not_ready",
                "message": "Complete the interview before editing policy fields.",
            },
        )

    try:
        return _save_session(
            repository,
            update_policy_field_value(
                session,
                field_id,
                request.value,
                request.status,
            ),
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_policy_field_value",
                "message": str(exc).replace("_", " ").capitalize(),
            },
        ) from exc


@router.post("/onboarding/sessions/{session_id}/source-inventory")
def create_source_inventory_item(
    session_id: str,
    request: SourceInventoryCreateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(
            repository,
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
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_source_inventory_item",
                "message": "The source permission metadata is inconsistent.",
            },
        ) from exc


@router.patch("/onboarding/sessions/{session_id}/source-inventory/{source_id}")
def patch_source_inventory_item(
    session_id: str,
    source_id: str,
    request: SourceInventoryUpdateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(
            repository,
            update_source_inventory_item(
                session,
                source_id,
                **request.model_dump(exclude_unset=True),
            ),
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_source_inventory_item",
                "message": "The source permission metadata is inconsistent.",
            },
        ) from exc


@router.patch("/onboarding/sessions/{session_id}/approval-checklist/{item_id}")
def patch_approval_checklist_item(
    session_id: str,
    item_id: str,
    request: ApprovalChecklistUpdateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(
            repository,
            update_approval_checklist_item(session, item_id, request.checked),
        )
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


@router.patch(
    "/onboarding/sessions/{session_id}/preview-cases/{preview_case_id}/decision"
)
def patch_preview_decision(
    session_id: str,
    preview_case_id: str,
    request: PreviewDecisionRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(
            repository,
            set_preview_decision(
                session,
                preview_case_id,
                request.decision,
                request.reason,
            ),
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


@router.post("/onboarding/sessions/{session_id}/preview-cases")
def create_custom_preview_case(
    session_id: str,
    request: CustomPreviewRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(
            repository,
            add_custom_preview_case(
                session,
                prompt=request.prompt,
                tag=request.tag,
            ),
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
        if str(exc) == "custom_preview_limit_reached":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "custom_preview_limit_reached",
                    "message": "A session can contain at most 20 custom previews.",
                },
            ) from exc
        if str(exc) == "custom_preview_prompt_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "custom_preview_prompt_required",
                    "message": "Enter a non-empty preview prompt.",
                },
            ) from exc
        raise


@router.post("/onboarding/sessions/{session_id}/revision-proposal/confirm")
def confirm_revision(
    session_id: str,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(repository, confirm_revision_proposal(session))
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


@router.post("/onboarding/sessions/{session_id}/revision-proposal/discard")
def discard_revision(
    session_id: str,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return _save_session(repository, discard_revision_proposal(session))
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
