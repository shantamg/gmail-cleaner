"""Interactive CLI for Gmail Cleaner."""

from typing import Any

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
from gmail_cleaner.types import Config, Category, EmailData


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
    import subprocess
    import time

    answer = questionary.confirm(
        "Ollama not running. Start it now?",
        default=True
    ).ask()
    if answer:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("Started Ollama. Waiting for it to be ready...")
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

    choices = [
        Choice(title=f"{name} ({acc.email})", value=name)
        for name, acc in config.accounts.items()
    ]
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
                Choice(
                    title=f"Max emails per run (current: {config.max_emails_per_run})",
                    value="max"
                ),
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
    from gmail_cleaner.pending import pending_exists, load_pending, apply_pending, delete_pending
    from gmail_cleaner.gmail import fetch_emails, apply_actions
    from gmail_cleaner.classifier import classify_emails, generate_summaries

    # Check for pending results
    if pending_exists():
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
                count = apply_pending(pending, config)
                print(f"Applied to {count} emails.")
            return
        elif choice == "discard":
            delete_pending()
        elif choice == "cancel":
            return

    # Select account
    if not config.accounts:
        print("No accounts configured. Add an account first.")
        return

    account_name: str | None
    if len(config.accounts) == 1:
        account_name = list(config.accounts.keys())[0]
    else:
        choices = [
            Choice(title=f"{name} ({acc.email})", value=name)
            for name, acc in config.accounts.items()
        ]
        choices.append(Choice(title="Cancel", value=None))
        account_name = questionary.select(
            "Select account:",
            choices=choices
        ).ask()

    if not account_name:
        return

    # Run classification flow
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
        count = apply_actions(config, account_name, results)
        print(f"Done. Applied to {count} emails.")
    elif choice == "save":
        from gmail_cleaner.pending import save_pending
        save_pending(account_name, emails, results)
        print("Results saved. Use 'Apply pending results' from main menu to apply later.")


def drill_down_menu(
    emails: list[EmailData],
    results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Allow user to drill down and edit classifications."""
    while True:
        categories: dict[str, list[tuple[EmailData, dict[str, Any]]]] = {}
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
                title=f"{e.sender[:30]} - {e.subject[:40]}",
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
            f"Action for: {email.subject[:50]}",
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
        choices: list[Choice[str | None]] = [
            Choice(title="Run cleaner", value="run"),
        ]

        if pending_exists():
            choices.insert(0, Choice(title="Apply pending results", value="apply_pending"))

        choices.extend([
            Choice(title="Add account", value="add"),
        ])

        if len(config.accounts) > 1:
            choices.append(Choice(title="Remove account", value="remove"))

        choices.extend([
            Choice(title="Settings", value="settings"),
            Choice(title="Exit", value="exit"),
        ])

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
                count = apply_pending(pending, config)
                print(f"Applied to {count} emails.")
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
    elif not check_model_available(config.model):
        print(f"Model '{config.model}' not found. Install with: ollama pull {config.model}")

    # Show main menu
    main_menu(config)


if __name__ == "__main__":
    main()
