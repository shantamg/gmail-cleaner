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

        return category, str(reason)
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
                    if not line.startswith(("*", "-", "•")):
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
