"""Gmail API integration for Gmail Cleaner."""

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build, Resource  # type: ignore[import-untyped]

from gmail_cleaner.config import get_config_dir
from gmail_cleaner.types import AccountConfig, Config, EmailData, TokenData

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
    creds = Credentials(  # type: ignore[no-untyped-call]
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

            headers = {
                h["name"]: h["value"]
                for h in msg_data.get("payload", {}).get("headers", [])
            }

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
                return str(label["id"])

        # Create label if it doesn't exist
        label_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        result = service.users().labels().create(userId="me", body=label_body).execute()
        return str(result["id"])
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
