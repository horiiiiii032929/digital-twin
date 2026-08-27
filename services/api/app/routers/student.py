from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from services.api.app.dependencies import (
    ProactiveOutreachServiceDependency,
    StudentAccountDependency,
    StudentServiceDependency,
)
from services.api.app.schemas import OutreachPreferenceRequest, StudentMessageRequest
from src.digital_twin.student import (
    Citation,
    Conversation,
    ConversationView,
    OutreachChannel,
    OutreachPreference,
    ProactiveMessageView,
    ProactiveOutreachError,
    StudentCourse,
    StudentWorkflowError,
    TutorTurn,
)


router = APIRouter(prefix="/student", tags=["student"])


@router.get("/courses", response_model=list[StudentCourse])
def list_student_courses(
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    return _call(service.list_courses, account_id)


@router.get(
    "/courses/{course_id}/outreach-preferences",
    response_model=list[OutreachPreference],
)
def list_outreach_preferences(
    course_id: str,
    account_id: StudentAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    return _outreach_call(outreach.list_preferences, account_id, course_id)


@router.put(
    "/courses/{course_id}/outreach-preferences/{channel}",
    response_model=OutreachPreference,
)
def update_outreach_preference(
    course_id: str,
    channel: OutreachChannel,
    request: OutreachPreferenceRequest,
    account_id: StudentAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    return _outreach_call(
        outreach.update_preference,
        account_id,
        course_id,
        channel=channel,
        **request.model_dump(),
    )


@router.get("/outreach", response_model=list[ProactiveMessageView])
def list_outreach_inbox(
    account_id: StudentAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
    course_id: str | None = None,
):
    return _outreach_call(
        outreach.list_inbox, account_id, course_id=course_id
    )


@router.post(
    "/outreach/{message_id}/read", response_model=ProactiveMessageView
)
def mark_outreach_read(
    message_id: str,
    account_id: StudentAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    return _outreach_call(outreach.mark_read, account_id, message_id)


@router.post(
    "/outreach/{message_id}/dismiss", response_model=ProactiveMessageView
)
def dismiss_outreach(
    message_id: str,
    account_id: StudentAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    return _outreach_call(outreach.dismiss, account_id, message_id)


@router.post(
    "/courses/{course_id}/conversations",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
)
def create_student_conversation(
    course_id: str,
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    return _call(service.create_conversation, account_id, course_id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationView,
)
def get_student_conversation(
    conversation_id: str,
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    return _call(service.get_conversation, account_id, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=TutorTurn,
)
async def submit_student_message(
    conversation_id: str,
    request: StudentMessageRequest,
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    try:
        return await service.submit_message(
            account_id,
            conversation_id,
            content=request.content,
            client_request_id=request.request_id,
        )
    except StudentWorkflowError as error:
        raise _http_error(error) from error


@router.get("/messages/{message_id}/citations", response_model=list[Citation])
def list_student_message_citations(
    message_id: str,
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    return _call(service.list_citations, account_id, message_id)


@router.get("/messages/{message_id}/citations/{citation_id}/crop")
def get_student_citation_crop(
    message_id: str,
    citation_id: str,
    request: Request,
    account_id: StudentAccountDependency,
    service: StudentServiceDependency,
):
    citations = _call(service.list_citations, account_id, message_id)
    citation = next((item for item in citations if item.id == citation_id), None)
    if citation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "citation_not_found", "message": "Citation was not found."},
        )
    crop_path = _resolve_region_crop(request.app.state.region_crop_root, citation.crop_ref)
    if crop_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "citation_crop_unavailable",
                "message": "This approved citation does not have a displayable crop.",
            },
        )
    return FileResponse(
        crop_path,
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )


def _resolve_region_crop(root: Path, crop_ref: str | None) -> Path | None:
    prefix = "region://"
    if crop_ref is None or not crop_ref.startswith(prefix):
        return None
    filename = crop_ref.removeprefix(prefix)
    if not filename or Path(filename).name != filename or not filename.endswith(".png"):
        return None
    resolved_root = root.resolve()
    lexical_candidate = resolved_root / filename
    if lexical_candidate.is_symlink():
        return None
    candidate = lexical_candidate.resolve()
    if not candidate.is_relative_to(resolved_root) or not candidate.is_file():
        return None
    return candidate


def _call(operation, *args):
    try:
        return operation(*args)
    except StudentWorkflowError as error:
        raise _http_error(error) from error


def _outreach_call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ProactiveOutreachError as error:
        not_found = {
            "account_not_found",
            "proactive_message_not_found",
            "proactive_trigger_not_found",
        }
        conflict = {
            "release_unavailable",
            "proactive_message_state_invalid",
            "trigger_idempotency_conflict",
        }
        status_code = (
            status.HTTP_404_NOT_FOUND
            if error.code in not_found
            else status.HTTP_409_CONFLICT
            if error.code in conflict
            else status.HTTP_403_FORBIDDEN
            if error.code.endswith("forbidden")
            or error.code in {"student_account_required", "course_forbidden"}
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error


def _http_error(error: StudentWorkflowError) -> HTTPException:
    not_found = {"account_not_found", "message_not_found"}
    conflict = {
        "release_unavailable",
        "profile_mismatch",
        "citation_scope_violation",
        "request_id_conflict",
        "turn_persistence_conflict",
    }
    status_code = (
        status.HTTP_404_NOT_FOUND
        if error.code in not_found
        else status.HTTP_409_CONFLICT
        if error.code in conflict
        else status.HTTP_422_UNPROCESSABLE_CONTENT
        if error.code == "invalid_message"
        else status.HTTP_403_FORBIDDEN
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    )
