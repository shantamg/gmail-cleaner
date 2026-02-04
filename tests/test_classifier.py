"""Tests for classifier module."""

from unittest.mock import patch, MagicMock
from typing import Any

import pytest

from gmail_cleaner.classifier import (
    classify_single_email,
    classify_emails,
    generate_summaries,
    parse_classification_response,
    build_classification_prompt,
    build_summary_prompt,
)
from gmail_cleaner.types import EmailData, Category


@pytest.fixture
def sample_email() -> EmailData:
    """Sample email for testing."""
    return EmailData(
        id="abc123",
        thread_id="thread123",
        sender="john@example.com",
        subject="Meeting Thursday?",
        snippet="Hi, are you free for a meeting on Thursday afternoon?",
        date="2026-02-03",
    )


@pytest.fixture
def sample_emails() -> list[EmailData]:
    """Sample list of emails for testing."""
    return [
        EmailData(
            id="abc123",
            thread_id="thread123",
            sender="john@example.com",
            subject="Meeting Thursday?",
            snippet="Hi, are you free for a meeting on Thursday?",
            date="2026-02-03",
        ),
        EmailData(
            id="def456",
            thread_id="thread456",
            sender="newsletter@company.com",
            subject="Weekly Newsletter",
            snippet="This week in tech news...",
            date="2026-02-03",
        ),
    ]


class TestBuildPrompt:
    """Tests for prompt building."""

    def test_build_classification_prompt_includes_email_data(
        self, sample_email: EmailData
    ) -> None:
        """build_classification_prompt includes sender, subject, snippet, date."""
        prompt = build_classification_prompt(sample_email)
        assert "john@example.com" in prompt
        assert "Meeting Thursday?" in prompt
        assert "are you free" in prompt
        assert "2026-02-03" in prompt

    def test_build_classification_prompt_includes_categories(
        self, sample_email: EmailData
    ) -> None:
        """build_classification_prompt includes all category options."""
        prompt = build_classification_prompt(sample_email)
        assert "NEEDS_REPLY" in prompt
        assert "NEEDS_ACTION" in prompt
        assert "FYI" in prompt
        assert "ARCHIVE" in prompt
        assert "IGNORE" in prompt


class TestParseResponse:
    """Tests for response parsing."""

    def test_parse_valid_json_response(self) -> None:
        """parse_classification_response extracts category from valid JSON."""
        response = '{"category": "NEEDS_REPLY", "reason": "Requires response"}'
        category, reason = parse_classification_response(response)
        assert category == Category.NEEDS_REPLY
        assert reason == "Requires response"

    def test_parse_invalid_json_defaults_to_fyi(self) -> None:
        """parse_classification_response returns FYI for invalid JSON."""
        response = "not valid json"
        category, reason = parse_classification_response(response)
        assert category == Category.FYI
        assert "parse" in reason.lower() or "invalid" in reason.lower()

    def test_parse_json_with_unknown_category_defaults_to_fyi(self) -> None:
        """parse_classification_response returns FYI for unknown category."""
        response = '{"category": "UNKNOWN", "reason": "Something"}'
        category, reason = parse_classification_response(response)
        assert category == Category.FYI


class TestClassifyEmails:
    """Tests for email classification."""

    @patch("gmail_cleaner.classifier.ollama")
    def test_classify_single_email_calls_ollama(
        self, mock_ollama: MagicMock, sample_email: EmailData
    ) -> None:
        """classify_single_email calls ollama.chat with correct prompt."""
        mock_ollama.chat.return_value = {
            "message": {"content": '{"category": "NEEDS_REPLY", "reason": "test"}'}
        }

        result = classify_single_email(sample_email, "mistral:7b")

        mock_ollama.chat.assert_called_once()
        call_args = mock_ollama.chat.call_args
        assert call_args.kwargs["model"] == "mistral:7b"
        assert "Meeting Thursday?" in str(call_args.kwargs["messages"])

    @patch("gmail_cleaner.classifier.ollama")
    def test_classify_emails_returns_results_for_all(
        self, mock_ollama: MagicMock, sample_emails: list[EmailData]
    ) -> None:
        """classify_emails returns classification for each email."""
        mock_ollama.chat.return_value = {
            "message": {"content": '{"category": "FYI", "reason": "test"}'}
        }

        results = classify_emails(sample_emails, "mistral:7b")

        assert len(results) == len(sample_emails)
        for result in results:
            assert "email_id" in result
            assert "category" in result

    @patch("gmail_cleaner.classifier.ollama")
    def test_classify_emails_handles_ollama_error(
        self, mock_ollama: MagicMock, sample_emails: list[EmailData]
    ) -> None:
        """classify_emails handles Ollama errors gracefully."""
        mock_ollama.chat.side_effect = Exception("Connection error")

        results = classify_emails(sample_emails, "mistral:7b")

        # Should return FYI as default for failed classifications
        assert len(results) == len(sample_emails)
        for result in results:
            assert result["category"] == "FYI"


class TestGenerateSummaries:
    """Tests for summary generation."""

    @patch("gmail_cleaner.classifier.ollama")
    def test_generate_summaries_formats_output(
        self, mock_ollama: MagicMock, sample_emails: list[EmailData]
    ) -> None:
        """generate_summaries returns formatted summary string."""
        mock_ollama.chat.return_value = {
            "message": {"content": "* Email about meeting\n* Newsletter update"}
        }

        results = [
            {"email_id": "abc123", "category": "NEEDS_REPLY", "reason": "test"},
            {"email_id": "def456", "category": "ARCHIVE", "reason": "test"},
        ]

        summary = generate_summaries(sample_emails, results, "mistral:7b")

        assert "NEEDS REPLY" in summary
        assert "ARCHIVE" in summary

    @patch("gmail_cleaner.classifier.ollama")
    def test_generate_summaries_shows_counts_for_archive_ignore(
        self, mock_ollama: MagicMock, sample_emails: list[EmailData]
    ) -> None:
        """generate_summaries shows only counts for ARCHIVE and IGNORE."""
        mock_ollama.chat.return_value = {
            "message": {"content": "* Email summary"}
        }

        results = [
            {"email_id": "abc123", "category": "ARCHIVE", "reason": "test"},
            {"email_id": "def456", "category": "IGNORE", "reason": "test"},
        ]

        summary = generate_summaries(sample_emails, results, "mistral:7b")

        assert "ARCHIVE: 1 email" in summary or "ARCHIVE (1" in summary
        assert "IGNORE: 1 email" in summary or "IGNORE (1" in summary
