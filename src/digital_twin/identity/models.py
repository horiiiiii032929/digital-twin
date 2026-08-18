"""Credential and session models for invite-only product access."""

from __future__ import annotations

from pydantic import BaseModel, Field

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


class SessionRecord(BaseModel):
    token_digest: str = Field(min_length=64, max_length=64)
    account_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)
    last_seen_at: str = Field(min_length=1)
    revoked_at: str | None = None


class IssuedSession(BaseModel):
    token: str = Field(min_length=32)
    expires_at: str = Field(min_length=1)
    principal: IdentityProfile
