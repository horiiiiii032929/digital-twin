"""Invite-only credential and opaque-session service."""

from __future__ import annotations

import base64
import binascii
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
    AuditEvent,
)
from src.digital_twin.student.repository import StudentRepository


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PASSWORD_MIN_LENGTH = 12
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_BYTES = 16
_SCRYPT_HASH_BYTES = 32
_DUMMY_SALT = b"\x00" * _SCRYPT_SALT_BYTES
_DUMMY_HASH = hashlib.scrypt(
    b"Invalid-password-0",
    salt=_DUMMY_SALT,
    n=_SCRYPT_N,
    r=_SCRYPT_R,
    p=_SCRYPT_P,
    dklen=_SCRYPT_HASH_BYTES,
)
_DUMMY_PASSWORD_HASH = "$".join(
    (
        "scrypt-v1",
        str(_SCRYPT_N),
        str(_SCRYPT_R),
        str(_SCRYPT_P),
        base64.urlsafe_b64encode(_DUMMY_SALT).decode("ascii"),
        base64.urlsafe_b64encode(_DUMMY_HASH).decode("ascii"),
    )
)


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
        if (
            isinstance(session_ttl_seconds, bool)
            or not isinstance(session_ttl_seconds, int)
            or session_ttl_seconds <= 0
        ):
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
        audit_event: AuditEvent | None = None,
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
        now = _timestamp()
        self.identity_repository.save_account_credential(
            Account(id=identifier, role=role, status=AccountStatus.ACTIVE),
            CredentialRecord(
                account_id=identifier,
                email=email.strip(),
                normalized_email=normalized_email,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                created_at=existing.created_at if existing else now,
                updated_at=now,
            ),
            audit_event,
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
        identifier = f"account-{uuid4()}"
        return self.provision_account(
            account_id=identifier,
            email=email,
            display_name=display_name,
            role=role,
            password=temporary_password,
            audit_event=_audit_event(
                "identity.account_invited",
                actor_id,
                target_account_id=identifier,
                target_role=role.value,
            ),
        )

    def login(self, email: str, password: str) -> IssuedSession:
        credential = self.identity_repository.get_credential_by_email(
            _normalize_email(email)
        )
        password_hash = (
            credential.password_hash if credential is not None else _DUMMY_PASSWORD_HASH
        )
        password_valid = verify_password(password, password_hash)
        if credential is None or not password_valid:
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
            ),
            _audit_event("identity.login", account.id),
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
        if session is None or session.revoked_at is not None:
            raise IdentityError("session_invalid", "Your session is invalid or expired.")
        try:
            expires_at = datetime.fromisoformat(session.expires_at)
            if expires_at.tzinfo is None or expires_at <= now:
                raise ValueError("session expiry is absent or expired")
        except (TypeError, ValueError):
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
        if not token:
            return
        digest = _token_digest(token)
        session = self.identity_repository.get_session(digest)
        account_id = session.account_id if session is not None else None
        self.identity_repository.revoke_session(
            digest,
            _timestamp(),
            (
                _audit_event("identity.logout", account_id)
                if account_id is not None
                else None
            ),
        )

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
        self._replace_password(
            credential,
            new_password,
            audit_event=_audit_event("identity.password_changed", account_id),
        )

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
        self._replace_password(
            credential,
            new_password,
            audit_event=_audit_event(
                "identity.password_reset",
                actor_id,
                target_account_id=account_id,
            ),
        )

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
        if not self.identity_repository.revoke_account_and_sessions(
            account_id,
            _timestamp(),
            _audit_event(
                "identity.account_revoked",
                actor_id,
                target_account_id=account_id,
            ),
        ):
            raise IdentityError("account_not_found", "The account was not found.")

    def profile_for_account(self, account_id: str) -> IdentityProfile:
        credential = self.identity_repository.get_credential(account_id)
        account = self.account_repository.get_account(account_id)
        if credential is None or account is None:
            raise IdentityError("account_not_found", "The account was not found.")
        return _profile(credential, account.role)

    def _replace_password(
        self,
        credential: CredentialRecord,
        new_password: str,
        *,
        audit_event: AuditEvent,
    ) -> None:
        _validate_password(new_password)
        now = _timestamp()
        self.identity_repository.replace_credential_and_revoke_sessions(
            credential.model_copy(
                update={
                    "password_hash": hash_password(new_password),
                    "updated_at": now,
                }
            ),
            now,
            audit_event,
        )


def hash_password(password: str) -> str:
    _validate_password(password)
    salt = secrets.token_bytes(_SCRYPT_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_HASH_BYTES,
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
        if (
            algorithm != "scrypt-v1"
            or int(raw_n) != _SCRYPT_N
            or int(raw_r) != _SCRYPT_R
            or int(raw_p) != _SCRYPT_P
        ):
            return False
        salt = base64.b64decode(raw_salt, altchars=b"-_", validate=True)
        expected = base64.b64decode(raw_hash, altchars=b"-_", validate=True)
        if len(salt) != _SCRYPT_SALT_BYTES or len(expected) != _SCRYPT_HASH_BYTES:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_SCRYPT_HASH_BYTES,
        )
    except (binascii.Error, ValueError, TypeError):
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


def _audit_event(
    event_type: str,
    account_id: str,
    **details: str | None,
) -> AuditEvent:
    return AuditEvent(
        id=f"audit-{uuid4()}",
        event_type=event_type,
        account_id=account_id,
        details={key: value for key, value in details.items() if value is not None},
    )
