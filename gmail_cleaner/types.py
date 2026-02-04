"""Type definitions for Gmail Cleaner."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypedDict


class Category(Enum):
    """Email classification categories."""

    NEEDS_REPLY = "NEEDS_REPLY"
    NEEDS_ACTION = "NEEDS_ACTION"
    FYI = "FYI"
    ARCHIVE = "ARCHIVE"
    IGNORE = "IGNORE"


DEFAULT_LABELS: dict[Category, str] = {
    Category.NEEDS_REPLY: "Auto/Needs Reply",
    Category.NEEDS_ACTION: "Auto/Needs Action",
    Category.FYI: "Auto/FYI",
    Category.ARCHIVE: "Auto/Archive",
    Category.IGNORE: "Auto/Ignore",
}


class TokenData(TypedDict):
    """OAuth token data structure."""

    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    expiry: str


@dataclass
class AccountConfig:
    """Configuration for a single Gmail account."""

    email: str
    token: TokenData


@dataclass
class Config:
    """Main configuration structure."""

    model: str = "mistral:7b"
    max_emails_per_run: int = 100
    labels: dict[str, str] = field(default_factory=lambda: {
        cat.value: label for cat, label in DEFAULT_LABELS.items()
    })
    accounts: dict[str, AccountConfig] = field(default_factory=dict)


@dataclass
class EmailData:
    """Email data fetched from Gmail."""

    id: str
    thread_id: str
    sender: str
    subject: str
    snippet: str
    date: str


@dataclass
class ClassificationResult:
    """Result of classifying an email."""

    email_id: str
    category: Category
    reason: str


@dataclass
class PendingEmail:
    """Email pending action in pending.json."""

    account: str
    email_id: str
    category: Category
    skip: bool
    subject: str
    sender: str


@dataclass
class PendingResults:
    """Pending classification results."""

    created_at: datetime
    results: list[PendingEmail] = field(default_factory=list)
