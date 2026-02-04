# Gmail Cleaner CLI - Design Document

## Overview

A Python CLI tool that connects to multiple Gmail accounts via OAuth 2.0, fetches unread emails, classifies them using a local Ollama model, and automatically applies labels and archives based on the classification.

## Goals

- Manage inbox across 3 Gmail accounts with identical rules
- Auto-categorize emails into action-based categories
- Apply Gmail labels for easy filtering in Gmail web
- Archive low-value emails automatically
- Provide simple summary output after each run
- Single interactive CLI with arrow-key navigation

## Technical Stack

- **Language:** Python 3.11+
- **Gmail API:** `google-api-python-client` with OAuth 2.0
- **LLM:** Ollama with `mistral:7b` (recommended)
- **CLI Framework:** `questionary` for interactive menus
- **Config Storage:** JSON file at `~/.gmail-cleaner/config.json`

## Project Structure

```
gmail-cleaner/
├── gmail_cleaner/
│   ├── __init__.py
│   ├── cli.py          # Interactive CLI menus
│   ├── gmail.py        # Gmail API wrapper
│   ├── classifier.py   # Ollama integration
│   └── config.py       # Account & settings management
├── config.json         # Stores account configs & OAuth tokens
├── pyproject.toml
└── README.md
```

## Authentication

### OAuth 2.0 Setup

1. User creates a Google Cloud project
2. Enables Gmail API
3. Creates OAuth 2.0 Desktop credentials
4. Downloads `credentials.json` to `~/.gmail-cleaner/`

### Gmail API Scopes

- `gmail.readonly` - Read emails
- `gmail.modify` - Apply labels, archive, mark read/unread
- `gmail.labels` - Create/manage labels

### Token Storage

Each account's OAuth token stored in `~/.gmail-cleaner/config.json`:

```json
{
  "model": "mistral:7b",
  "accounts": {
    "personal": {
      "email": "you@gmail.com",
      "token": { "access_token": "...", "refresh_token": "...", ... }
    },
    "work": {
      "email": "you@company.com",
      "token": { ... }
    },
    "side-project": {
      "email": "project@gmail.com",
      "token": { ... }
    }
  }
}
```

## Email Classification

### Data Sent to LLM

For each unread email:
- Sender (name + email address)
- Subject line
- Snippet (first ~200 chars of body)
- Date received

Full body is NOT sent - keeps processing fast and avoids context limits.

### Prompt Template

```
Classify this email into exactly one category:
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
{"category": "...", "reason": "one sentence"}
```

### Categories

| Category | Description |
|----------|-------------|
| NEEDS_REPLY | Requires a response from me |
| NEEDS_ACTION | Requires me to do something (not a reply) |
| FYI | Informational, read later, no action needed |
| ARCHIVE | Low value, newsletters I don't read, notifications |
| IGNORE | Spam, marketing, completely irrelevant |

### Fallback Behavior

- Ollama unreachable: Exit with clear error message
- Invalid JSON response: Default to "FYI" (safe, non-destructive)
- Hedging language in reason: Default to "FYI"

## Gmail Actions

### Labels

Labels are created automatically on first run with `Auto/` prefix:

| Category | Gmail Label |
|----------|-------------|
| NEEDS_REPLY | `Auto/Needs Reply` |
| NEEDS_ACTION | `Auto/Needs Action` |
| FYI | `Auto/FYI` |
| ARCHIVE | `Auto/Archive` |
| IGNORE | `Auto/Ignore` |

### Actions Per Category

| Category | Label Applied | Additional Action |
|----------|---------------|-------------------|
| NEEDS_REPLY | `Auto/Needs Reply` | Stays in inbox |
| NEEDS_ACTION | `Auto/Needs Action` | Stays in inbox |
| FYI | `Auto/FYI` | Stays in inbox |
| ARCHIVE | `Auto/Archive` | Archived (removed from inbox) |
| IGNORE | `Auto/Ignore` | Archived (removed from inbox) |

### Idempotency

Emails are skipped if they already have any `Auto/*` label. Gmail query:

```
is:inbox AND NOT label:Auto/Needs-Reply AND NOT label:Auto/Needs-Action AND NOT label:Auto/FYI AND NOT label:Auto/Archive AND NOT label:Auto/Ignore
```

No local tracking file needed - Gmail labels are the source of truth.

## CLI Interface

### Entry Point

Single command launches interactive menu:

```bash
gmail-cleaner
```

### Main Menu

```
Gmail Cleaner
─────────────
❯ Run cleaner (all accounts)
  Run cleaner (select account)
  Dry run (preview only)
  ─────────────
  Add account
  Remove account
  Settings
  ─────────────
  Exit
```

### Account Selection

```
Select account:
❯ All accounts
  personal@gmail.com
  work@company.com
  side@gmail.com
```

"All accounts" is always first/default.

### Settings Menu

```
Settings
────────
❯ Change Ollama model (current: mistral:7b)
  View label mappings
  Back
```

### Output After Run

```
Processing 3 accounts...

personal@gmail.com (47 emails)
  Needs Reply:  3
  Needs Action: 5
  FYI:          8
  Archive:     12
  Ignore:      19

work@company.com (23 emails)
  Needs Reply:  7
  Needs Action: 2
  FYI:          6
  Archive:      4
  Ignore:       4

side@gmail.com (11 emails)
  Needs Reply:  1
  Needs Action: 0
  FYI:          3
  Archive:      2
  Ignore:       5

Done. Labels applied in Gmail.
```

## First-Run Setup

Running `gmail-cleaner` with no configuration triggers guided setup:

```
Google Cloud Setup Required
───────────────────────────
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new project (or select existing)
3. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the JSON and save as: ~/.gmail-cleaner/credentials.json

Press Enter when ready...
```

Then validates credentials and prompts to add first account.

If Ollama model not found:

```
Ollama model 'mistral:7b' not found.
Install it with: ollama pull mistral:7b
```

## Implementation Plan

### Phase 1: Project Setup
- Initialize Python project with pyproject.toml
- Set up dependencies (google-api-python-client, ollama, questionary)
- Create directory structure

### Phase 2: Configuration
- Implement config.py for reading/writing ~/.gmail-cleaner/config.json
- Implement guided setup flow
- Validate credentials.json format

### Phase 3: Gmail Integration
- Implement OAuth flow for adding accounts
- Implement email fetching with skip logic
- Implement label creation
- Implement label application and archiving

### Phase 4: Ollama Classification
- Implement classifier.py with prompt template
- Implement JSON parsing with fallbacks
- Implement batch processing

### Phase 5: CLI Interface
- Implement interactive menus with questionary
- Implement run flow tying everything together
- Implement dry-run mode
- Implement summary output

### Phase 6: Polish
- Error handling and user-friendly messages
- Edge cases (no emails, API errors, etc.)
- Test with real accounts
