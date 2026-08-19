from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_PACKAGE_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _https_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("public source URLs must use HTTPS")
    return value.strip()


class PlayAppImportItem(BaseModel):
    store: Literal["google_play"] = "google_play"
    package_name: str = Field(min_length=3, max_length=255)
    app_name: str = Field(min_length=1, max_length=300)
    developer_name: str = Field(min_length=1, max_length=300)
    developer_id: str | None = Field(default=None, max_length=300)
    support_email: str | None = Field(default=None, max_length=320)
    developer_website: str | None = Field(default=None, max_length=1000)
    privacy_policy_url: str | None = Field(default=None, max_length=1000)
    store_url: str = Field(max_length=1000)
    category: str | None = Field(default=None, max_length=160)
    installs: str | None = Field(default=None, max_length=80)
    source_provider: str = Field(min_length=1, max_length=120)
    source_url: str = Field(max_length=1000)
    observed_at: datetime

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, value: str) -> str:
        value = value.strip()
        if not _PACKAGE_RE.fullmatch(value):
            raise ValueError("package_name must look like an Android package id")
        return value

    @field_validator("support_email")
    @classmethod
    def validate_support_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().lower()
        if not _EMAIL_RE.fullmatch(value):
            raise ValueError("support_email must be a public email address")
        return value

    @field_validator("store_url", "source_url")
    @classmethod
    def validate_required_urls(cls, value: str) -> str:
        return _https_url(value)

    @field_validator("developer_website", "privacy_policy_url")
    @classmethod
    def validate_optional_urls(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _https_url(value)


class PlayAppImportBatch(BaseModel):
    records: list[PlayAppImportItem] = Field(min_length=1, max_length=500)


class AppOwnershipReviewInput(BaseModel):
    decision: Literal["confirmed", "rejected"]


class AppRegistrySearchResult(BaseModel):
    id: str
    store: str
    package_name: str
    loan_relevance: str
    app_name: str | None
    developer_name: str | None
    support_email: str | None
    email_domain: str | None
    developer_website: str | None
    developer_domain: str | None
    store_url: str | None
    last_seen_at: datetime
    ownership_links: list[dict[str, object]]
