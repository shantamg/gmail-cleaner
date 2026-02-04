"""Tests for config module."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from gmail_cleaner.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    CREDENTIALS_FILE,
    load_config,
    save_config,
    get_config_dir,
    ensure_config_dir,
    credentials_exist,
    validate_credentials,
    get_default_config,
)
from gmail_cleaner.types import Config, Category


class TestConfigDir:
    """Tests for config directory functions."""

    def test_get_config_dir_returns_path(self) -> None:
        """get_config_dir returns Path to ~/.gmail-cleaner."""
        result = get_config_dir()
        assert isinstance(result, Path)
        assert result.name == ".gmail-cleaner"

    def test_ensure_config_dir_creates_directory(self, tmp_path: Path) -> None:
        """ensure_config_dir creates the directory if it doesn't exist."""
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path / ".gmail-cleaner"):
            from gmail_cleaner.config import ensure_config_dir
            result = ensure_config_dir()
            assert result.exists()
            assert result.is_dir()


class TestCredentials:
    """Tests for credentials validation."""

    def test_credentials_exist_returns_false_when_missing(self, tmp_path: Path) -> None:
        """credentials_exist returns False when file doesn't exist."""
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            assert credentials_exist() is False

    def test_credentials_exist_returns_true_when_present(self, tmp_path: Path) -> None:
        """credentials_exist returns True when file exists."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            assert credentials_exist() is True

    def test_validate_credentials_returns_error_for_invalid_json(self, tmp_path: Path) -> None:
        """validate_credentials returns error for malformed JSON."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("not valid json")
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            result = validate_credentials()
            assert result is not None
            assert "malformed" in result.lower() or "invalid" in result.lower()

    def test_validate_credentials_returns_none_for_valid(self, tmp_path: Path) -> None:
        """validate_credentials returns None for valid credentials."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"installed": {"client_id": "test"}}')
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            result = validate_credentials()
            assert result is None


class TestConfig:
    """Tests for config load/save."""

    def test_get_default_config_returns_config(self) -> None:
        """get_default_config returns a Config with defaults."""
        result = get_default_config()
        assert isinstance(result, Config)
        assert result.model == "mistral:7b"
        assert result.max_emails_per_run == 100
        assert len(result.labels) == 5

    def test_load_config_returns_default_when_missing(self, tmp_path: Path) -> None:
        """load_config returns default config when file doesn't exist."""
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            result = load_config()
            assert result.model == "mistral:7b"
            assert result.accounts == {}

    def test_load_config_reads_existing_file(self, tmp_path: Path) -> None:
        """load_config reads and parses existing config file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "model": "llama2:7b",
            "max_emails_per_run": 50,
            "labels": {
                "NEEDS_REPLY": "Auto/Needs Reply",
                "NEEDS_ACTION": "Auto/Needs Action",
                "FYI": "Auto/FYI",
                "ARCHIVE": "Auto/Archive",
                "IGNORE": "Auto/Ignore",
            },
            "accounts": {}
        }
        config_file.write_text(json.dumps(config_data))
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            result = load_config()
            assert result.model == "llama2:7b"
            assert result.max_emails_per_run == 50

    def test_save_config_writes_file(self, tmp_path: Path) -> None:
        """save_config writes config to JSON file."""
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            config = Config(model="test-model", max_emails_per_run=25)
            save_config(config)

            config_file = tmp_path / "config.json"
            assert config_file.exists()
            data = json.loads(config_file.read_text())
            assert data["model"] == "test-model"
            assert data["max_emails_per_run"] == 25

    def test_save_config_preserves_accounts(self, tmp_path: Path) -> None:
        """save_config preserves account data."""
        with patch("gmail_cleaner.config.get_config_dir", return_value=tmp_path):
            from gmail_cleaner.types import AccountConfig, TokenData
            token: TokenData = {
                "access_token": "test",
                "refresh_token": "test",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test",
                "client_secret": "test",
                "scopes": [],
                "expiry": "2026-01-01T00:00:00Z"
            }
            config = Config(
                accounts={"personal": AccountConfig(email="test@gmail.com", token=token)}
            )
            save_config(config)

            loaded = load_config()
            assert "personal" in loaded.accounts
            assert loaded.accounts["personal"].email == "test@gmail.com"
