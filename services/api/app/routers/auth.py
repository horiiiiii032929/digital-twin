"""Credentialed invite-only authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from services.api.app.dependencies import (
    AdminAccountDependency,
    CurrentAccountDependency,
    IdentityServiceDependency,
    SettingsDependency,
)
from services.api.app.schemas import (
    AccountInviteRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
)
from src.digital_twin.identity import IdentityError, IdentityProfile


router = APIRouter(tags=["identity"])


@router.post("/auth/login", response_model=IdentityProfile)
def login(
    payload: LoginRequest,
    response: Response,
    identity: IdentityServiceDependency,
    settings: SettingsDependency,
):
    if not settings.credential_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "credential_auth_disabled",
                "message": "Credential login is disabled in local demo mode.",
            },
        )
    try:
        issued = identity.login(payload.email, payload.password)
    except IdentityError as error:
        raise _identity_http_error(error) from error
    response.set_cookie(
        settings.session_cookie_name,
        issued.token,
        max_age=settings.session_ttl_seconds,
        expires=settings.session_ttl_seconds,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return issued.principal


@router.get("/auth/session", response_model=IdentityProfile)
def current_session(
    request: Request,
    response: Response,
    identity: IdentityServiceDependency,
    settings: SettingsDependency,
):
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        profile = identity.authenticate(token)
    except IdentityError as error:
        raise _identity_http_error(error) from error
    response.headers["Cache-Control"] = "no-store"
    return profile


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    identity: IdentityServiceDependency,
    settings: SettingsDependency,
):
    token = request.cookies.get(settings.session_cookie_name, "")
    identity.logout(token)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    account_id: CurrentAccountDependency,
    identity: IdentityServiceDependency,
    settings: SettingsDependency,
):
    try:
        identity.change_password(
            account_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except IdentityError as error:
        raise _identity_http_error(error) from error
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/admin/accounts",
    response_model=IdentityProfile,
    status_code=status.HTTP_201_CREATED,
)
def invite_account(
    payload: AccountInviteRequest,
    account_id: AdminAccountDependency,
    identity: IdentityServiceDependency,
):
    try:
        invited = identity.invite_account(
            account_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            temporary_password=payload.temporary_password,
        )
    except IdentityError as error:
        raise _identity_http_error(error) from error
    return invited


@router.post(
    "/admin/accounts/{target_account_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reset_password(
    target_account_id: str,
    payload: PasswordResetRequest,
    account_id: AdminAccountDependency,
    identity: IdentityServiceDependency,
):
    try:
        identity.reset_password(
            account_id,
            target_account_id,
            new_password=payload.new_password,
        )
    except IdentityError as error:
        raise _identity_http_error(error) from error


@router.delete(
    "/admin/accounts/{target_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_account(
    target_account_id: str,
    account_id: AdminAccountDependency,
    identity: IdentityServiceDependency,
):
    if target_account_id == account_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "self_revoke_forbidden",
                "message": "Administrators cannot revoke their own active account.",
            },
        )
    try:
        identity.revoke_account(account_id, target_account_id)
    except IdentityError as error:
        raise _identity_http_error(error) from error


def _identity_http_error(error: IdentityError) -> HTTPException:
    if error.code in {
        "invalid_credentials",
        "invalid_current_password",
        "session_required",
        "session_invalid",
    }:
        code = status.HTTP_401_UNAUTHORIZED
    elif error.code in {"account_inactive", "admin_required"}:
        code = status.HTTP_403_FORBIDDEN
    elif error.code == "account_not_found":
        code = status.HTTP_404_NOT_FOUND
    else:
        code = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )
