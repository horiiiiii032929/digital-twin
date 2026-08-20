"""Credential and session models for invite-only product access."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.student.models import AccountRole


class IdentityProfile(BaseModel):
    account_id: str = Field(min_length=1)
    email: str = Field(min_length=3)
    display_name: str = Field(min_length=1)
    role: AccountRole


class CredentialRecord(BaseModel):
    account_id: str = Field(min_length=1)
    email: str = Field(min_length=3)
    normalized_email: str = Field(min_length=3)
    display_name: str = Field(min_length=1)
    password_hash: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def identity_fields_must_be_canonical(self) -> "CredentialRecord":
        if self.normalized_email != self.email.strip().casefold():
            raise ValueError("normalized_email must match the account email")
        created = _timestamp(self.created_at)
        updated = _timestamp(self.updated_at)
        if updated < created:
            raise ValueError("credential updated_at cannot precede created_at")
        return self


class SessionRecord(BaseModel):
    token_digest: str = Field(min_length=64, max_length=64)
    account_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)
    last_seen_at: str = Field(min_length=1)
    revoked_at: str | None = None

    @field_validator("token_digest")
    @classmethod
    def token_digest_must_be_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValueError("token_digest must be a SHA-256 digest")
        return normalized

    @model_validator(mode="after")
    def session_timestamps_must_be_ordered(self) -> "SessionRecord":
        created = _timestamp(self.created_at)
        expires = _timestamp(self.expires_at)
        last_seen = _timestamp(self.last_seen_at)
        if expires <= created:
            raise ValueError("session expiry must follow creation")
        if last_seen < created:
            raise ValueError("session last_seen_at cannot precede creation")
        if self.revoked_at is not None and _timestamp(self.revoked_at) < created:
            raise ValueError("session revoked_at cannot precede creation")
        return self


class IssuedSession(BaseModel):
    token: str = Field(min_length=32)
    expires_at: str = Field(min_length=1)
    principal: IdentityProfile


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("identity timestamps must be ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("identity timestamps must include a timezone")
    return parsed
