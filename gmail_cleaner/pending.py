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
