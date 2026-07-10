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
from src.digital_twin.onboarding import OnboardingSession, SessionRepository
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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/onboarding/sessions", status_code=status.HTTP_201_CREATED)
def create_onboarding_session(repository: SessionRepositoryDependency):
    return repository.save(create_session())


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
    return repository.save(submit_message(session, request.content))


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
        return repository.save(
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


@router.post("/onboarding/sessions/{session_id}/source-inventory")
def create_source_inventory_item(
    session_id: str,
    request: SourceInventoryCreateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    return repository.save(
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


@router.patch("/onboarding/sessions/{session_id}/source-inventory/{source_id}")
def patch_source_inventory_item(
    session_id: str,
    source_id: str,
    request: SourceInventoryUpdateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return repository.save(
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


@router.patch("/onboarding/sessions/{session_id}/approval-checklist/{item_id}")
def patch_approval_checklist_item(
    session_id: str,
    item_id: str,
    request: ApprovalChecklistUpdateRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return repository.save(
            update_approval_checklist_item(session, item_id, request.checked)
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
        return repository.save(
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


@router.post("/onboarding/sessions/{session_id}/preview-cases")
def create_custom_preview_case(
    session_id: str,
    request: CustomPreviewRequest,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return repository.save(
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


@router.post("/onboarding/sessions/{session_id}/revision-proposal/confirm")
def confirm_revision(
    session_id: str,
    repository: SessionRepositoryDependency,
):
    session = _get_session_or_404(repository, session_id)
    try:
        return repository.save(confirm_revision_proposal(session))
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
        return repository.save(discard_revision_proposal(session))
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
