# Gmail Cleaner CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI that classifies Gmail emails using local Ollama LLM and applies labels/archiving automatically.

**Architecture:** Multi-module CLI using questionary for interactive menus, google-api-python-client for Gmail OAuth, and ollama library for LLM classification. Config stored in ~/.gmail-cleaner/. TDD with mocked external APIs.

**Tech Stack:** Python 3.11+, questionary, google-api-python-client, google-auth-oauthlib, ollama, pytest, mypy (strict mode)

---

## Phase 1: Foundation & Config

### Task 1: Initialize Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `gmail_cleaner/__init__.py`
- Create: `gmail_cleaner/__main__.py`
- Create: `gmail_cleaner/types.py`
- Create: `gmail_cleaner/config.py`
- Create: `gmail_cleaner/cli.py`
- Create: `gmail_cleaner/gmail.py`
- Create: `gmail_cleaner/classifier.py`
- Create: `gmail_cleaner/pending.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `tests/test_classifier.py`
- Create: `tests/test_pending.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gmail-cleaner"
version = "0.1.0"
description = "CLI tool for classifying and managing Gmail emails using local LLM"
requires-python = ">=3.11"
dependencies = [
    "google-api-python-client>=2.100.0",
    "google-auth-oauthlib>=1.1.0",
    "ollama>=0.1.0",
    "questionary>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "mypy>=1.7.0",
    "pytest-mock>=3.12.0",
]

[tool.mypy]
strict = true
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
```

**Step 2: Create module stub files**

Create empty `__init__.py` files and minimal stubs:

`gmail_cleaner/__init__.py`:
```python
"""Gmail Cleaner - CLI tool for classifying Gmail emails using local LLM."""

__version__ = "0.1.0"
```

`gmail_cleaner/__main__.py`:
```python
"""Entry point for gmail_cleaner CLI."""

from gmail_cleaner.cli import main


if __name__ == "__main__":
    main()
```

`tests/__init__.py`:
```python
"""Gmail Cleaner test suite."""
```

**Step 3: Create virtual environment and install dependencies**

Run:
```bash
cd /Users/shantam/Software/gmail-cleaner
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Step 4: Commit**

```bash
git add pyproject.toml gmail_cleaner/ tests/
git commit -m "feat: initialize project structure with dependencies"
```

---

### Task 2: Implement Type Definitions

**Files:**
- Create: `gmail_cleaner/types.py`

**Step 1: Write types.py with all data structures**

```python
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
```

**Step 2: Verify types pass mypy**

Run: `mypy gmail_cleaner/types.py --strict`
Expected: Success, 0 errors

**Step 3: Commit**

```bash
git add gmail_cleaner/types.py
git commit -m "feat: add type definitions for config, email, and classification"
```

---

### Task 3: Implement Config Module - Tests First

**Files:**
- Create: `tests/test_config.py`

**Step 1: Write failing tests for config module**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (module not implemented)

**Step 3: Commit failing tests**

```bash
git add tests/test_config.py
git commit -m "test: add failing tests for config module"
```

---

### Task 4: Implement Config Module

**Files:**
- Create: `gmail_cleaner/config.py`

**Step 1: Implement config.py**

```python
"""Configuration management for Gmail Cleaner."""

import json
from dataclasses import asdict
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
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All tests PASS

**Step 3: Run mypy**

Run: `mypy gmail_cleaner/ --strict`
Expected: Success, 0 errors

**Step 4: Commit**

```bash
git add gmail_cleaner/config.py
git commit -m "feat: implement config module with load/save/validate"
```

---

### Task 5: Implement CLI Stub with Main Menu

**Files:**
- Modify: `gmail_cleaner/cli.py`

**Step 1: Write cli.py with main menu structure**

```python
"""Interactive CLI for Gmail Cleaner."""

import questionary
from questionary import Choice

from gmail_cleaner.config import (
    credentials_exist,
    validate_credentials,
    load_config,
    save_config,
    get_config_dir,
    ensure_config_dir,
)
from gmail_cleaner.types import Config


SETUP_INSTRUCTIONS = """
Gmail Cleaner Setup
===================

To use Gmail Cleaner, you need to set up Google Cloud credentials:

1. Go to the Google Cloud Console:
   https://console.cloud.google.com/

2. Create a new project or select an existing one

3. Enable the Gmail API:
   https://console.cloud.google.com/apis/library/gmail.googleapis.com

4. Create OAuth 2.0 credentials:
   https://console.cloud.google.com/apis/credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the JSON file

5. Save the downloaded file as:
   {config_dir}/credentials.json

After saving credentials.json, run this tool again.
"""


def show_setup_instructions() -> None:
    """Display setup instructions for first-time users."""
    config_dir = get_config_dir()
    print(SETUP_INSTRUCTIONS.format(config_dir=config_dir))


def check_ollama_status() -> bool:
    """Check if Ollama is running and model is available."""
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False


def prompt_start_ollama() -> bool:
    """Prompt user to start Ollama if not running."""
    answer = questionary.confirm(
        "Ollama not running. Start it now?",
        default=True
    ).ask()
    if answer:
        import subprocess
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Started Ollama. Waiting for it to be ready...")
        import time
        time.sleep(2)
        return check_ollama_status()
    return False


def check_model_available(model: str) -> bool:
    """Check if the specified model is available in Ollama."""
    try:
        import ollama
        models = ollama.list()
        model_names = [m.get("name", "") for m in models.get("models", [])]
        return any(model in name or name in model for name in model_names)
    except Exception:
        return False


def add_account(config: Config) -> Config:
    """Add a new Gmail account via OAuth flow."""
    from gmail_cleaner.gmail import authenticate_account

    nickname = questionary.text(
        "Enter a nickname for this account (e.g., 'personal', 'work'):"
    ).ask()

    if not nickname:
        print("Account addition cancelled.")
        return config

    nickname = nickname.strip().lower().replace(" ", "-")

    if nickname in config.accounts:
        print(f"Account '{nickname}' already exists. Choose a different name.")
        return config

    account = authenticate_account()
    if account:
        config.accounts[nickname] = account
        save_config(config)
        print(f"Account '{nickname}' added successfully!")
    else:
        print("Authentication failed. Please try again.")

    return config


def remove_account(config: Config) -> Config:
    """Remove a Gmail account."""
    if len(config.accounts) <= 1:
        print("Cannot remove last account.")
        return config

    choices = [Choice(title=f"{name} ({acc.email})", value=name)
               for name, acc in config.accounts.items()]
    choices.append(Choice(title="Cancel", value=None))

    account_name = questionary.select(
        "Select account to remove:",
        choices=choices
    ).ask()

    if not account_name:
        return config

    confirm = questionary.confirm(
        f"Remove {config.accounts[account_name].email}?",
        default=False
    ).ask()

    if confirm:
        del config.accounts[account_name]
        save_config(config)
        print(f"Account '{account_name}' removed.")

    return config


def settings_menu(config: Config) -> Config:
    """Show settings menu."""
    while True:
        choice = questionary.select(
            "Settings:",
            choices=[
                Choice(title=f"Change model (current: {config.model})", value="model"),
                Choice(title="Customize label names", value="labels"),
                Choice(title=f"Max emails per run (current: {config.max_emails_per_run})", value="max"),
                Choice(title="Back", value="back"),
            ]
        ).ask()

        if choice == "back" or choice is None:
            break
        elif choice == "model":
            new_model = questionary.text(
                "Enter model name:",
                default=config.model
            ).ask()
            if new_model and check_model_available(new_model):
                config.model = new_model
                save_config(config)
                print(f"Model changed to {new_model}")
            elif new_model:
                print(f"Model '{new_model}' not found in Ollama.")
        elif choice == "labels":
            config = edit_labels(config)
        elif choice == "max":
            new_max = questionary.text(
                "Enter max emails per run:",
                default=str(config.max_emails_per_run)
            ).ask()
            try:
                max_val = int(new_max) if new_max else config.max_emails_per_run
                if max_val > 0:
                    config.max_emails_per_run = max_val
                    save_config(config)
                    print(f"Max emails set to {max_val}")
                else:
                    print("Must be a positive number.")
            except ValueError:
                print("Invalid number.")

    return config


def edit_labels(config: Config) -> Config:
    """Edit label name mappings."""
    print("\nCurrent label mappings:")
    for cat, label in config.labels.items():
        print(f"  {cat}: {label}")
    print()

    for cat in config.labels:
        new_label = questionary.text(
            f"Label for {cat}:",
            default=config.labels[cat]
        ).ask()
        if new_label:
            config.labels[cat] = new_label

    save_config(config)
    print("Labels updated.")
    return config


def run_cleaner(config: Config) -> None:
    """Run the email classification and cleanup flow."""
    from gmail_cleaner.gmail import check_pending_exists
    from gmail_cleaner.pending import load_pending, apply_pending

    # Check for pending results
    if check_pending_exists():
        choice = questionary.select(
            "You have pending results. What would you like to do?",
            choices=[
                Choice(title="Apply pending results", value="apply"),
                Choice(title="Discard pending results", value="discard"),
                Choice(title="Cancel", value="cancel"),
            ]
        ).ask()

        if choice == "apply":
            pending = load_pending()
            if pending:
                apply_pending(pending, config)
            return
        elif choice == "discard":
            from gmail_cleaner.pending import delete_pending
            delete_pending()
        elif choice == "cancel":
            return

    # Select account
    if not config.accounts:
        print("No accounts configured. Add an account first.")
        return

    if len(config.accounts) == 1:
        account_name = list(config.accounts.keys())[0]
    else:
        choices = [Choice(title=f"{name} ({acc.email})", value=name)
                   for name, acc in config.accounts.items()]
        choices.append(Choice(title="Cancel", value=None))
        account_name = questionary.select(
            "Select account:",
            choices=choices
        ).ask()

    if not account_name:
        return

    # Run classification flow
    from gmail_cleaner.gmail import fetch_emails, apply_actions
    from gmail_cleaner.classifier import classify_emails, generate_summaries

    print(f"\nFetching emails from {config.accounts[account_name].email}...")
    emails = fetch_emails(config, account_name)

    if not emails:
        print("No unprocessed emails found.")
        return

    print(f"Found {len(emails)} emails to process.")

    # Check Ollama
    if not check_ollama_status():
        if not prompt_start_ollama():
            print("Cannot proceed without Ollama running.")
            return

    if not check_model_available(config.model):
        print(f"Model '{config.model}' not found. Install with: ollama pull {config.model}")
        return

    print(f"\nClassifying emails using {config.model}...")
    results = classify_emails(emails, config.model)

    # Generate and display summaries
    summaries = generate_summaries(emails, results, config.model)
    print("\n" + summaries)

    # Drill-down option
    results = drill_down_menu(emails, results)

    # Final action
    choice = questionary.select(
        "What would you like to do?",
        choices=[
            Choice(title="Apply now", value="apply"),
            Choice(title="Save for later", value="save"),
            Choice(title="Discard", value="discard"),
        ]
    ).ask()

    if choice == "apply":
        apply_actions(config, account_name, results)
        print(f"Done. Applied to {len([r for r in results if not r.get('skip', False)])} emails.")
    elif choice == "save":
        from gmail_cleaner.pending import save_pending
        save_pending(account_name, emails, results)
        print("Results saved. Use 'Apply pending results' from main menu to apply later.")


def drill_down_menu(emails: list, results: list) -> list:
    """Allow user to drill down and edit classifications."""
    from gmail_cleaner.types import Category

    while True:
        categories = {}
        for email, result in zip(emails, results):
            cat = result.get("category", "FYI")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((email, result))

        choices = [
            Choice(title=f"{cat} ({len(items)} emails)", value=cat)
            for cat, items in categories.items()
        ]
        choices.append(Choice(title="Done - continue", value=None))

        cat_choice = questionary.select(
            "Drill down into category?",
            choices=choices
        ).ask()

        if cat_choice is None:
            break

        # Show emails in category
        cat_emails = categories[cat_choice]
        email_choices = [
            Choice(
                title=f"{e['sender'][:30]} - {e['subject'][:40]}",
                value=i
            )
            for i, (e, _) in enumerate(cat_emails)
        ]
        email_choices.append(Choice(title="Back", value=None))

        email_idx = questionary.select(
            f"Emails in {cat_choice}:",
            choices=email_choices
        ).ask()

        if email_idx is None:
            continue

        email, result = cat_emails[email_idx]

        # Edit options
        other_cats = [c.value for c in Category if c.value != cat_choice]
        action_choices = [
            Choice(title=f"Change to {c}", value=c)
            for c in other_cats
        ]
        action_choices.extend([
            Choice(title="Skip this email", value="skip"),
            Choice(title="Back", value=None),
        ])

        action = questionary.select(
            f"Action for: {email['subject'][:50]}",
            choices=action_choices
        ).ask()

        if action == "skip":
            result["skip"] = True
        elif action and action != "skip":
            result["category"] = action

    return results


def main_menu(config: Config) -> None:
    """Show main menu and handle user choices."""
    from gmail_cleaner.pending import pending_exists

    while True:
        choices = [
            Choice(title="Run cleaner", value="run"),
        ]

        if pending_exists():
            choices.insert(0, Choice(title="Apply pending results", value="apply_pending"))

        choices.extend([
            Choice(title="Add account", value="add"),
            Choice(title="Remove account", value="remove") if len(config.accounts) > 1 else None,
            Choice(title="Settings", value="settings"),
            Choice(title="Exit", value="exit"),
        ])
        choices = [c for c in choices if c is not None]

        choice = questionary.select(
            "Gmail Cleaner - Main Menu",
            choices=choices
        ).ask()

        if choice == "exit" or choice is None:
            break
        elif choice == "run":
            run_cleaner(config)
        elif choice == "apply_pending":
            from gmail_cleaner.pending import load_pending, apply_pending, delete_pending
            pending = load_pending()
            if pending:
                apply_pending(pending, config)
                delete_pending()
        elif choice == "add":
            config = add_account(config)
        elif choice == "remove":
            config = remove_account(config)
        elif choice == "settings":
            config = settings_menu(config)


def main() -> None:
    """Main entry point for Gmail Cleaner CLI."""
    ensure_config_dir()

    # Check for credentials
    if not credentials_exist():
        show_setup_instructions()
        return

    # Validate credentials
    error = validate_credentials()
    if error:
        print(f"Error: {error}")
        return

    # Load config
    config = load_config()

    # First-time setup: add first account
    if not config.accounts:
        print("Welcome to Gmail Cleaner!\n")
        add_first = questionary.confirm(
            "Add your first account?",
            default=True
        ).ask()

        if add_first:
            config = add_account(config)

        if not config.accounts:
            print("No accounts configured. Run again to add an account.")
            return

    # Check Ollama
    if not check_ollama_status():
        if not prompt_start_ollama():
            print("Warning: Ollama is not running. Start it before classifying emails.")
    else:
        if not check_model_available(config.model):
            print(f"Model '{config.model}' not found. Install with: ollama pull {config.model}")

    # Show main menu
    main_menu(config)


if __name__ == "__main__":
    main()
```

**Step 2: Run mypy**

Run: `mypy gmail_cleaner/cli.py --strict`
Expected: Some errors about missing gmail.py and pending.py (OK for now)

**Step 3: Commit**

```bash
git add gmail_cleaner/cli.py
git commit -m "feat: add CLI structure with main menu and setup flow"
```

---

## Phase 2: Gmail Integration

### Task 6: Implement Gmail Module - Tests First

**Files:**
- Create: `gmail_cleaner/gmail.py`

**Step 1: Write gmail.py with OAuth and email operations**

```python
"""Gmail API integration for Gmail Cleaner."""

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from gmail_cleaner.config import get_config_dir, load_config, save_config
from gmail_cleaner.types import AccountConfig, Config, EmailData, TokenData, Category

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


def get_credentials_path() -> Path:
    """Get path to credentials.json."""
    return get_config_dir() / "credentials.json"


def authenticate_account() -> AccountConfig | None:
    """Authenticate a Gmail account and return AccountConfig."""
    creds_path = get_credentials_path()
    if not creds_path.exists():
        return None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        creds = flow.run_local_server(port=0)

        # Get user email
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "unknown@gmail.com")

        # Build token data
        token_data: TokenData = {
            "access_token": creds.token or "",
            "refresh_token": creds.refresh_token or "",
            "token_uri": creds.token_uri or "https://oauth2.googleapis.com/token",
            "client_id": creds.client_id or "",
            "client_secret": creds.client_secret or "",
            "scopes": list(creds.scopes) if creds.scopes else [],
            "expiry": creds.expiry.isoformat() if creds.expiry else "",
        }

        return AccountConfig(email=email, token=token_data)
    except Exception as e:
        print(f"Authentication error: {e}")
        return None


def get_gmail_service(account: AccountConfig) -> Resource:
    """Get authenticated Gmail API service for an account."""
    creds = Credentials(
        token=account.token["access_token"],
        refresh_token=account.token["refresh_token"],
        token_uri=account.token["token_uri"],
        client_id=account.token["client_id"],
        client_secret=account.token["client_secret"],
        scopes=account.token["scopes"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)


def build_exclusion_query(labels: dict[str, str]) -> str:
    """Build Gmail query to exclude already-processed emails."""
    label_names = list(labels.values())
    exclusions = " AND ".join([f'NOT label:"{label}"' for label in label_names])
    return f"is:inbox AND {exclusions}"


def fetch_emails(config: Config, account_name: str) -> list[EmailData]:
    """Fetch unprocessed emails from inbox."""
    account = config.accounts.get(account_name)
    if not account:
        return []

    try:
        service = get_gmail_service(account)
        query = build_exclusion_query(config.labels)

        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=config.max_emails_per_run
        ).execute()

        messages = results.get("messages", [])
        emails: list[EmailData] = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}

            emails.append(EmailData(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                sender=headers.get("From", "Unknown"),
                subject=headers.get("Subject", "(no subject)"),
                snippet=msg_data.get("snippet", "")[:200],
                date=headers.get("Date", ""),
            ))

        return emails
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []


def ensure_label_exists(service: Resource, label_name: str) -> str:
    """Ensure a label exists and return its ID."""
    try:
        # List existing labels
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        for label in labels:
            if label.get("name") == label_name:
                return label["id"]

        # Create label if it doesn't exist
        label_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        result = service.users().labels().create(userId="me", body=label_body).execute()
        return result["id"]
    except Exception as e:
        print(f"Error creating label {label_name}: {e}")
        return ""


def apply_label_and_archive(
    service: Resource,
    email_id: str,
    label_id: str,
    should_archive: bool
) -> bool:
    """Apply label to email and optionally archive it."""
    try:
        modify_body: dict[str, Any] = {
            "addLabelIds": [label_id],
        }
        if should_archive:
            modify_body["removeLabelIds"] = ["INBOX"]

        service.users().messages().modify(
            userId="me",
            id=email_id,
            body=modify_body
        ).execute()
        return True
    except Exception as e:
        print(f"Error modifying email {email_id}: {e}")
        return False


def apply_actions(
    config: Config,
    account_name: str,
    results: list[dict[str, Any]]
) -> int:
    """Apply classification results to Gmail."""
    account = config.accounts.get(account_name)
    if not account:
        return 0

    service = get_gmail_service(account)

    # Ensure all labels exist
    label_ids: dict[str, str] = {}
    for cat, label_name in config.labels.items():
        label_id = ensure_label_exists(service, label_name)
        if label_id:
            label_ids[cat] = label_id

    applied_count = 0
    for result in results:
        if result.get("skip", False):
            continue

        category = result.get("category", "FYI")
        email_id = result.get("email_id", "")
        label_id = label_ids.get(category, "")

        if not label_id or not email_id:
            continue

        should_archive = category in ("ARCHIVE", "IGNORE")
        if apply_label_and_archive(service, email_id, label_id, should_archive):
            applied_count += 1

    return applied_count


def check_pending_exists() -> bool:
    """Check if pending.json exists."""
    from gmail_cleaner.pending import pending_exists
    return pending_exists()
```

**Step 2: Run mypy**

Run: `mypy gmail_cleaner/gmail.py --strict`
Expected: May have errors about pending.py (OK, will fix next)

**Step 3: Commit**

```bash
git add gmail_cleaner/gmail.py
git commit -m "feat: implement Gmail API integration with OAuth and email operations"
```

---

## Phase 3: Classification & Summary

### Task 7: Implement Classifier Module - Tests First

**Files:**
- Create: `tests/test_classifier.py`

**Step 1: Write failing tests for classifier**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_classifier.py -v`
Expected: FAIL (module not implemented)

**Step 3: Commit failing tests**

```bash
git add tests/test_classifier.py
git commit -m "test: add failing tests for classifier module"
```

---

### Task 8: Implement Classifier Module

**Files:**
- Create: `gmail_cleaner/classifier.py`

**Step 1: Implement classifier.py**

```python
"""Email classification using Ollama LLM."""

import json
from typing import Any

import ollama

from gmail_cleaner.types import Category, EmailData


CLASSIFICATION_PROMPT = """Classify this email into exactly one category:
- NEEDS_REPLY: Requires a response from me
- NEEDS_ACTION: Requires me to do something (not a reply)
- FYI: Informational, read later, no action needed
- ARCHIVE: Low value, newsletters I don't read, notifications
- IGNORE: Spam, marketing, completely irrelevant

Email:
From: {sender}
Subject: {subject}
Preview: {snippet}
Date: {date}

Respond with JSON only:
{{"category": "...", "reason": "one sentence"}}"""


SUMMARY_PROMPT = """Summarize these emails in a bullet list. Each bullet should be one short sentence describing what the email is about.

Emails:
{emails}

Respond with bullet points only, one per email."""


def build_classification_prompt(email: EmailData) -> str:
    """Build the classification prompt for an email."""
    return CLASSIFICATION_PROMPT.format(
        sender=email.sender,
        subject=email.subject,
        snippet=email.snippet,
        date=email.date,
    )


def build_summary_prompt(emails: list[EmailData]) -> str:
    """Build the summary prompt for a list of emails."""
    email_list = "\n".join([
        f"- From: {e.sender}, Subject: {e.subject}, Preview: {e.snippet[:100]}"
        for e in emails
    ])
    return SUMMARY_PROMPT.format(emails=email_list)


def parse_classification_response(response: str) -> tuple[Category, str]:
    """Parse LLM response to extract category and reason."""
    try:
        # Try to extract JSON from response
        response = response.strip()

        # Handle case where response has extra text
        if "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            response = response[start:end]

        data = json.loads(response)
        category_str = data.get("category", "FYI")
        reason = data.get("reason", "")

        # Validate category
        try:
            category = Category(category_str)
        except ValueError:
            return Category.FYI, f"Unknown category: {category_str}"

        return category, reason
    except (json.JSONDecodeError, ValueError) as e:
        return Category.FYI, f"Failed to parse response: {str(e)}"


def classify_single_email(email: EmailData, model: str) -> dict[str, Any]:
    """Classify a single email using Ollama."""
    prompt = build_classification_prompt(email)

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.get("message", {}).get("content", "")
        category, reason = parse_classification_response(content)

        return {
            "email_id": email.id,
            "category": category.value,
            "reason": reason,
            "skip": False,
        }
    except Exception as e:
        return {
            "email_id": email.id,
            "category": Category.FYI.value,
            "reason": f"Classification failed: {str(e)}",
            "skip": False,
        }


def classify_emails(
    emails: list[EmailData],
    model: str,
    batch_size: int = 5,
    progress_callback: Any = None,
) -> list[dict[str, Any]]:
    """Classify a list of emails using Ollama."""
    results: list[dict[str, Any]] = []
    total = len(emails)

    for i, email in enumerate(emails):
        result = classify_single_email(email, model)
        results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)
        else:
            print(f"\rClassifying... [{i + 1}/{total}]", end="", flush=True)

    print()  # Newline after progress
    return results


def generate_summaries(
    emails: list[EmailData],
    results: list[dict[str, Any]],
    model: str,
) -> str:
    """Generate LLM summaries for important categories."""
    # Group emails by category
    categories: dict[str, list[EmailData]] = {}
    email_map = {e.id: e for e in emails}

    for result in results:
        cat = result.get("category", "FYI")
        email = email_map.get(result.get("email_id", ""))
        if email:
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(email)

    output_lines: list[str] = []

    # Generate summaries for important categories
    important_cats = ["NEEDS_REPLY", "NEEDS_ACTION", "FYI"]

    for cat in important_cats:
        if cat not in categories or not categories[cat]:
            continue

        cat_emails = categories[cat]
        count = len(cat_emails)
        display_name = cat.replace("_", " ")

        output_lines.append(f"\n{display_name} ({count} email{'s' if count != 1 else ''}):")

        try:
            prompt = build_summary_prompt(cat_emails)
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = response.get("message", {}).get("content", "")
            # Ensure bullets are formatted correctly
            for line in summary.strip().split("\n"):
                line = line.strip()
                if line:
                    if not line.startswith("*") and not line.startswith("-") and not line.startswith("•"):
                        line = f"• {line}"
                    else:
                        line = f"• {line.lstrip('*-• ')}"
                    output_lines.append(line)
        except Exception:
            for email in cat_emails:
                output_lines.append(f"• {email.sender}: {email.subject[:50]}")

    # Show counts only for ARCHIVE and IGNORE
    for cat in ["ARCHIVE", "IGNORE"]:
        if cat in categories:
            count = len(categories[cat])
            output_lines.append(f"\n{cat}: {count} email{'s' if count != 1 else ''}")

    return "\n".join(output_lines)
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_classifier.py -v`
Expected: All tests PASS

**Step 3: Run mypy**

Run: `mypy gmail_cleaner/classifier.py --strict`
Expected: Success, 0 errors

**Step 4: Commit**

```bash
git add gmail_cleaner/classifier.py
git commit -m "feat: implement classifier with Ollama integration and summaries"
```

---

## Phase 4: Pending Results

### Task 9: Implement Pending Module - Tests First

**Files:**
- Create: `tests/test_pending.py`

**Step 1: Write failing tests for pending module**

```python
"""Tests for pending results module."""

import json
from datetime import datetime
from pathlib import Path
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
def sample_results() -> list[dict]:
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
        sample_results: list[dict],
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
        sample_results: list[dict],
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
        sample_results: list[dict],
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pending.py -v`
Expected: FAIL (module not implemented)

**Step 3: Commit failing tests**

```bash
git add tests/test_pending.py
git commit -m "test: add failing tests for pending module"
```

---

### Task 10: Implement Pending Module

**Files:**
- Create: `gmail_cleaner/pending.py`

**Step 1: Implement pending.py**

```python
"""Pending results management for Gmail Cleaner."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from gmail_cleaner.config import get_config_dir
from gmail_cleaner.types import Category, Config, EmailData, PendingEmail, PendingResults


PENDING_FILE = "pending.json"


def get_pending_path() -> Path:
    """Get path to pending.json file."""
    return get_config_dir() / PENDING_FILE


def pending_exists() -> bool:
    """Check if pending.json exists."""
    return get_pending_path().exists()


def save_pending(
    account_name: str,
    emails: list[EmailData],
    results: list[dict[str, Any]],
) -> None:
    """Save classification results to pending.json."""
    email_map = {e.id: e for e in emails}

    pending_emails: list[dict[str, Any]] = []
    for result in results:
        email_id = result.get("email_id", "")
        email = email_map.get(email_id)
        if email:
            pending_emails.append({
                "account": account_name,
                "email_id": email_id,
                "category": result.get("category", "FYI"),
                "skip": result.get("skip", False),
                "subject": email.subject,
                "sender": email.sender,
            })

    data = {
        "created_at": datetime.now().isoformat(),
        "results": pending_emails,
    }

    pending_path = get_pending_path()
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pending_path, "w") as f:
        json.dump(data, f, indent=2)


def load_pending() -> PendingResults | None:
    """Load pending results from file."""
    pending_path = get_pending_path()
    if not pending_path.exists():
        return None

    try:
        with open(pending_path) as f:
            data = json.load(f)

        results: list[PendingEmail] = []
        for item in data.get("results", []):
            try:
                category = Category(item.get("category", "FYI"))
            except ValueError:
                category = Category.FYI

            results.append(PendingEmail(
                account=item.get("account", ""),
                email_id=item.get("email_id", ""),
                category=category,
                skip=item.get("skip", False),
                subject=item.get("subject", ""),
                sender=item.get("sender", ""),
            ))

        created_at_str = data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except ValueError:
            created_at = datetime.now()

        return PendingResults(created_at=created_at, results=results)
    except (json.JSONDecodeError, KeyError):
        return None


def delete_pending() -> None:
    """Delete pending.json file."""
    pending_path = get_pending_path()
    if pending_path.exists():
        pending_path.unlink()


def apply_pending(pending: PendingResults, config: Config) -> int:
    """Apply pending results to Gmail. Returns count of applied emails."""
    from gmail_cleaner.gmail import apply_actions

    # Group by account
    accounts: dict[str, list[dict[str, Any]]] = {}
    for result in pending.results:
        if result.account not in accounts:
            accounts[result.account] = []
        accounts[result.account].append({
            "email_id": result.email_id,
            "category": result.category.value,
            "skip": result.skip,
        })

    total_applied = 0
    for account_name, results in accounts.items():
        if account_name in config.accounts:
            applied = apply_actions(config, account_name, results)
            total_applied += applied

    # Delete pending file after successful apply
    delete_pending()

    return total_applied
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_pending.py -v`
Expected: All tests PASS

**Step 3: Run mypy**

Run: `mypy gmail_cleaner/pending.py --strict`
Expected: Success, 0 errors

**Step 4: Commit**

```bash
git add gmail_cleaner/pending.py
git commit -m "feat: implement pending results save/load/apply"
```

---

### Task 11: Final Integration - Run All Tests and Mypy

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run mypy on entire codebase**

Run: `mypy gmail_cleaner/ --strict`
Expected: Success, 0 errors

**Step 3: Test CLI starts (manual verification)**

Run: `python -m gmail_cleaner`
Expected: Shows setup instructions (if no credentials) or main menu

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Gmail Cleaner CLI implementation"
```

---

## Verification Commands

After each phase, run:

```bash
# Type checking
mypy gmail_cleaner/ --strict

# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_config.py -v
pytest tests/test_classifier.py -v
pytest tests/test_pending.py -v
```

## Definition of Done Checklist

- [ ] All user story acceptance criteria pass
- [ ] All implementation phases verified
- [ ] Tests pass: `pytest`
- [ ] Type check passes: `mypy gmail_cleaner/ --strict`
- [ ] Tool runs end-to-end with real Gmail account (manual verification)
