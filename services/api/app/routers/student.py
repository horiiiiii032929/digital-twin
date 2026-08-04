from fastapi import APIRouter, HTTPException, status

from services.api.app.dependencies import (
    StudentAccountDependency,
    StudentServiceDependency,
)
from services.api.app.schemas import StudentMessageRequest
from src.digital_twin.student import (
    Citation,
    Conversation,
    ConversationView,
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


def _call(operation, *args):
    try:
        return operation(*args)
    except StudentWorkflowError as error:
        raise _http_error(error) from error


def _http_error(error: StudentWorkflowError) -> HTTPException:
    not_found = {"account_not_found", "message_not_found"}
    conflict = {
        "release_unavailable",
        "profile_mismatch",
        "citation_scope_violation",
        "request_id_conflict",
    }
    status_code = (
        status.HTTP_404_NOT_FOUND
        if error.code in not_found
        else status.HTTP_409_CONFLICT
        if error.code in conflict
        else status.HTTP_403_FORBIDDEN
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    )
