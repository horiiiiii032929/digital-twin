"""Invite-only credential and opaque-session service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.digital_twin.identity.models import (
    CredentialRecord,
    IdentityProfile,
    IssuedSession,
    SessionRecord,
)
from src.digital_twin.identity.repository import IdentityRepository
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AccountStatus,
)
from src.digital_twin.student.repository import StudentRepository


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PASSWORD_MIN_LENGTH = 12
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


class IdentityError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class IdentityService:
    def __init__(
        self,
        identity_repository: IdentityRepository,
        account_repository: StudentRepository,
        *,
        session_ttl_seconds: int = 8 * 60 * 60,
    ) -> None:
        if session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds must be positive")
        self.identity_repository = identity_repository
        self.account_repository = account_repository
        self.session_ttl_seconds = session_ttl_seconds

    def provision_account(
        self,
        *,
        email: str,
        display_name: str,
        role: AccountRole,
        password: str,
        account_id: str | None = None,
    ) -> IdentityProfile:
        normalized_email = _normalize_email(email)
        _validate_password(password)
        if not display_name.strip():
            raise IdentityError("display_name_required", "Display name is required.")
        existing = self.identity_repository.get_credential_by_email(normalized_email)
        if existing is not None and existing.account_id != account_id:
            raise IdentityError("email_exists", "An account already uses this email.")
        identifier = account_id or f"account-{uuid4()}"
        current = self.account_repository.get_account(identifier)
        if current is not None and current.role != role:
            raise IdentityError(
                "account_role_conflict", "The existing account has a different role."
            )
        self.account_repository.save_account(
            Account(id=identifier, role=role, status=AccountStatus.ACTIVE)
        )
        now = _timestamp()
        self.identity_repository.save_credential(
            CredentialRecord(
                account_id=identifier,
                email=email.strip(),
                normalized_email=normalized_email,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                created_at=existing.created_at if existing else now,
                updated_at=now,
            )
        )
        return IdentityProfile(
            account_id=identifier,
            email=email.strip(),
            display_name=display_name.strip(),
            role=role,
        )

    def invite_account(
        self,
        actor_id: str,
        *,
        email: str,
        display_name: str,
        role: AccountRole,
        temporary_password: str,
    ) -> IdentityProfile:
        actor = self.account_repository.get_account(actor_id)
        if (
            actor is None
            or actor.status != AccountStatus.ACTIVE
            or actor.role != AccountRole.ADMIN
        ):
            raise IdentityError("admin_required", "An active administrator is required.")
        return self.provision_account(
            email=email,
            display_name=display_name,
            role=role,
            password=temporary_password,
        )

    def login(self, email: str, password: str) -> IssuedSession:
        credential = self.identity_repository.get_credential_by_email(
            _normalize_email(email)
        )
        if credential is None or not verify_password(password, credential.password_hash):
            raise IdentityError("invalid_credentials", "Email or password is incorrect.")
        account = self.account_repository.get_account(credential.account_id)
        if account is None or account.status != AccountStatus.ACTIVE:
            raise IdentityError("account_inactive", "This account is not active.")
        token = secrets.token_urlsafe(48)
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=self.session_ttl_seconds)
        self.identity_repository.save_session(
            SessionRecord(
                token_digest=_token_digest(token),
                account_id=account.id,
                created_at=now.isoformat(),
                expires_at=expires.isoformat(),
                last_seen_at=now.isoformat(),
            )
        )
        return IssuedSession(
            token=token,
            expires_at=expires.isoformat(),
            principal=_profile(credential, account.role),
        )

    def authenticate(self, token: str) -> IdentityProfile:
        if not token:
            raise IdentityError("session_required", "Sign in to continue.")
        digest = _token_digest(token)
        session = self.identity_repository.get_session(digest)
        now = datetime.now(UTC)
        if (
            session is None
            or session.revoked_at is not None
            or datetime.fromisoformat(session.expires_at) <= now
        ):
            raise IdentityError("session_invalid", "Your session is invalid or expired.")
        account = self.account_repository.get_account(session.account_id)
        credential = self.identity_repository.get_credential(session.account_id)
        if (
            account is None
            or credential is None
            or account.status != AccountStatus.ACTIVE
        ):
            raise IdentityError("account_inactive", "This account is not active.")
        self.identity_repository.touch_session(digest, now.isoformat())
        return _profile(credential, account.role)

    def logout(self, token: str) -> None:
        if token:
            self.identity_repository.revoke_session(_token_digest(token), _timestamp())

    def change_password(
        self,
        account_id: str,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        credential = self.identity_repository.get_credential(account_id)
        if credential is None or not verify_password(
            current_password, credential.password_hash
        ):
            raise IdentityError(
                "invalid_current_password", "The current password is incorrect."
            )
        self._replace_password(credential, new_password)

    def reset_password(
        self,
        actor_id: str,
        account_id: str,
        *,
        new_password: str,
    ) -> None:
        actor = self.account_repository.get_account(actor_id)
        if (
            actor is None
            or actor.status != AccountStatus.ACTIVE
            or actor.role != AccountRole.ADMIN
        ):
            raise IdentityError("admin_required", "An active administrator is required.")
        credential = self.identity_repository.get_credential(account_id)
        if credential is None:
            raise IdentityError("account_not_found", "The account was not found.")
        self._replace_password(credential, new_password)

    def revoke_account(self, actor_id: str, account_id: str) -> None:
        actor = self.account_repository.get_account(actor_id)
        target = self.account_repository.get_account(account_id)
        if (
            actor is None
            or actor.status != AccountStatus.ACTIVE
            or actor.role != AccountRole.ADMIN
        ):
            raise IdentityError("admin_required", "An active administrator is required.")
        if target is None:
            raise IdentityError("account_not_found", "The account was not found.")
        self.account_repository.save_account(
            target.model_copy(update={"status": AccountStatus.REVOKED})
        )
        self.identity_repository.revoke_account_sessions(account_id, _timestamp())

    def profile_for_account(self, account_id: str) -> IdentityProfile:
        credential = self.identity_repository.get_credential(account_id)
        account = self.account_repository.get_account(account_id)
        if credential is None or account is None:
            raise IdentityError("account_not_found", "The account was not found.")
        return _profile(credential, account.role)

    def _replace_password(
        self, credential: CredentialRecord, new_password: str
    ) -> None:
        _validate_password(new_password)
        self.identity_repository.save_credential(
            credential.model_copy(
                update={
                    "password_hash": hash_password(new_password),
                    "updated_at": _timestamp(),
                }
            )
        )
        self.identity_repository.revoke_account_sessions(
            credential.account_id, _timestamp()
        )


def hash_password(password: str) -> str:
    _validate_password(password)
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return "$".join(
        (
            "scrypt-v1",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived).decode("ascii"),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_n, raw_r, raw_p, raw_salt, raw_hash = encoded.split("$")
        if algorithm != "scrypt-v1":
            return False
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(raw_hash.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not _EMAIL_PATTERN.fullmatch(normalized):
        raise IdentityError("invalid_email", "Enter a valid email address.")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise IdentityError(
            "weak_password",
            f"Password must contain at least {_PASSWORD_MIN_LENGTH} characters.",
        )
    if password.casefold() == password or password.upper() == password:
        raise IdentityError(
            "weak_password", "Password must include upper- and lowercase characters."
        )
    if not any(character.isdigit() for character in password):
        raise IdentityError("weak_password", "Password must include a number.")


def _profile(credential: CredentialRecord, role: AccountRole) -> IdentityProfile:
    return IdentityProfile(
        account_id=credential.account_id,
        email=credential.email,
        display_name=credential.display_name,
        role=role,
    )


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
