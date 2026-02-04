"""Configuration management for Gmail Cleaner."""

import json
from pathlib import Path
from typing import Any

from gmail_cleaner.types import (
    AccountConfig,
    Category,
    Config,
    DEFAULT_LABELS,
    TokenData,
)

CONFIG_DIR = ".gmail-cleaner"
CONFIG_FILE = "config.json"
CREDENTIALS_FILE = "credentials.json"


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return Path.home() / CONFIG_DIR


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists and return its path."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def credentials_exist() -> bool:
    """Check if credentials.json exists in config directory."""
    creds_path = get_config_dir() / CREDENTIALS_FILE
    return creds_path.exists()


def validate_credentials() -> str | None:
    """Validate credentials.json file. Returns error message or None if valid."""
    creds_path = get_config_dir() / CREDENTIALS_FILE
    if not creds_path.exists():
        return "credentials.json not found"

    try:
        with open(creds_path) as f:
            json.load(f)
        return None
    except json.JSONDecodeError:
        return "credentials.json contains malformed JSON"


def get_default_config() -> Config:
    """Return a new Config with default values."""
    return Config()


def _config_to_dict(config: Config) -> dict[str, Any]:
    """Convert Config to JSON-serializable dict."""
    result: dict[str, Any] = {
        "model": config.model,
        "max_emails_per_run": config.max_emails_per_run,
        "labels": config.labels,
        "accounts": {},
    }
    for name, account in config.accounts.items():
        result["accounts"][name] = {
            "email": account.email,
            "token": dict(account.token),
        }
    return result


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert dict from JSON to Config object."""
    accounts: dict[str, AccountConfig] = {}
    for name, account_data in data.get("accounts", {}).items():
        token_data: TokenData = {
            "access_token": account_data["token"]["access_token"],
            "refresh_token": account_data["token"]["refresh_token"],
            "token_uri": account_data["token"]["token_uri"],
            "client_id": account_data["token"]["client_id"],
            "client_secret": account_data["token"]["client_secret"],
            "scopes": account_data["token"]["scopes"],
            "expiry": account_data["token"]["expiry"],
        }
        accounts[name] = AccountConfig(
            email=account_data["email"],
            token=token_data,
        )

    return Config(
        model=data.get("model", "mistral:7b"),
        max_emails_per_run=data.get("max_emails_per_run", 100),
        labels=data.get("labels", {cat.value: label for cat, label in DEFAULT_LABELS.items()}),
        accounts=accounts,
    )


def load_config() -> Config:
    """Load configuration from file. Returns default config if file doesn't exist."""
    config_path = get_config_dir() / CONFIG_FILE
    if not config_path.exists():
        return get_default_config()

    try:
        with open(config_path) as f:
            data = json.load(f)
        return _dict_to_config(data)
    except (json.JSONDecodeError, KeyError):
        return get_default_config()


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_dir = ensure_config_dir()
    config_path = config_dir / CONFIG_FILE

    with open(config_path, "w") as f:
        json.dump(_config_to_dict(config), f, indent=2)
