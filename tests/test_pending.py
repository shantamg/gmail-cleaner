"""Tests for pending results module."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gmail_cleaner.pending import (
    pending_exists,
    load_pending,
    save_pending,
    delete_pending,
    get_pending_path,
)
from gmail_cleaner.types import EmailData, PendingResults, PendingEmail, Category


@pytest.fixture
def sample_emails() -> list[EmailData]:
    """Sample emails for testing."""
    return [
        EmailData(
            id="abc123",
            thread_id="thread123",
            sender="john@example.com",
            subject="Meeting Thursday?",
            snippet="Hi, are you free?",
            date="2026-02-03",
        ),
        EmailData(
            id="def456",
            thread_id="thread456",
            sender="newsletter@co.com",
            subject="Weekly Update",
            snippet="This week...",
            date="2026-02-03",
        ),
    ]


@pytest.fixture
def sample_results() -> list[dict[str, Any]]:
    """Sample classification results."""
    return [
        {"email_id": "abc123", "category": "NEEDS_REPLY", "reason": "test", "skip": False},
        {"email_id": "def456", "category": "ARCHIVE", "reason": "test", "skip": False},
    ]


class TestPendingExists:
    """Tests for pending_exists function."""

    def test_pending_exists_returns_false_when_no_file(self, tmp_path: Path) -> None:
        """pending_exists returns False when pending.json doesn't exist."""
        with patch("gmail_cleaner.pending.get_pending_path", return_value=tmp_path / "pending.json"):
            assert pending_exists() is False

    def test_pending_exists_returns_true_when_file_exists(self, tmp_path: Path) -> None:
        """pending_exists returns True when pending.json exists."""
        pending_file = tmp_path / "pending.json"
        pending_file.write_text("{}")
        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            assert pending_exists() is True


class TestSavePending:
    """Tests for save_pending function."""

    def test_save_pending_creates_file(
        self,
        tmp_path: Path,
        sample_emails: list[EmailData],
        sample_results: list[dict[str, Any]],
    ) -> None:
        """save_pending creates pending.json file."""
        pending_file = tmp_path / "pending.json"
        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            save_pending("personal", sample_emails, sample_results)
            assert pending_file.exists()

    def test_save_pending_includes_created_at(
        self,
        tmp_path: Path,
        sample_emails: list[EmailData],
        sample_results: list[dict[str, Any]],
    ) -> None:
        """save_pending includes created_at timestamp."""
        pending_file = tmp_path / "pending.json"
        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            save_pending("personal", sample_emails, sample_results)
            data = json.loads(pending_file.read_text())
            assert "created_at" in data

    def test_save_pending_includes_all_results(
        self,
        tmp_path: Path,
        sample_emails: list[EmailData],
        sample_results: list[dict[str, Any]],
    ) -> None:
        """save_pending includes all email results."""
        pending_file = tmp_path / "pending.json"
        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            save_pending("personal", sample_emails, sample_results)
            data = json.loads(pending_file.read_text())
            assert len(data["results"]) == 2
            assert data["results"][0]["email_id"] == "abc123"
            assert data["results"][0]["category"] == "NEEDS_REPLY"


class TestLoadPending:
    """Tests for load_pending function."""

    def test_load_pending_returns_none_when_no_file(self, tmp_path: Path) -> None:
        """load_pending returns None when file doesn't exist."""
        with patch("gmail_cleaner.pending.get_pending_path", return_value=tmp_path / "pending.json"):
            assert load_pending() is None

    def test_load_pending_returns_pending_results(self, tmp_path: Path) -> None:
        """load_pending returns PendingResults object."""
        pending_file = tmp_path / "pending.json"
        data = {
            "created_at": "2026-02-03T10:00:00",
            "results": [
                {
                    "account": "personal",
                    "email_id": "abc123",
                    "category": "NEEDS_REPLY",
                    "skip": False,
                    "subject": "Test",
                    "sender": "test@test.com",
                }
            ]
        }
        pending_file.write_text(json.dumps(data))

        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            result = load_pending()
            assert result is not None
            assert len(result.results) == 1
            assert result.results[0].email_id == "abc123"


class TestDeletePending:
    """Tests for delete_pending function."""

    def test_delete_pending_removes_file(self, tmp_path: Path) -> None:
        """delete_pending removes the pending.json file."""
        pending_file = tmp_path / "pending.json"
        pending_file.write_text("{}")

        with patch("gmail_cleaner.pending.get_pending_path", return_value=pending_file):
            delete_pending()
            assert not pending_file.exists()

    def test_delete_pending_handles_missing_file(self, tmp_path: Path) -> None:
        """delete_pending doesn't error when file doesn't exist."""
        with patch("gmail_cleaner.pending.get_pending_path", return_value=tmp_path / "pending.json"):
            delete_pending()  # Should not raise
