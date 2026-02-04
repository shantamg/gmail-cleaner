# Gmail Cleaner CLI - Product Requirements Document

*Finalized: 2026-02-03*

## Overview

A Python CLI tool that connects to multiple Gmail accounts via OAuth 2.0, fetches inbox emails, classifies them using a local Ollama model (mistral:7b), and automatically applies Gmail labels and archives based on the classification. The tool provides LLM-generated summaries of important categories and allows users to review, edit, and apply or save results.

## Problem Statement

Managing multiple Gmail inboxes is time-consuming. Emails pile up across 3 accounts, mixing important messages with newsletters, notifications, and spam. Manual triage is tedious and often neglected, leading to missed important emails and inbox anxiety.

## Scope

### In Scope
- Multi-account Gmail management (3 accounts, same rules)
- OAuth 2.0 authentication with guided setup
- Email classification via local Ollama LLM
- Automatic label creation and application
- Archiving of low-value emails
- LLM-generated summaries of important categories (Needs Reply, Needs Action, FYI)
- Interactive CLI with arrow-key navigation (questionary)
- Drill-down to view/edit individual email classifications
- Save pending results for later application
- Configurable settings (model, label names, batch limit)
- Unit tests for core logic with mocked external APIs
- Full type hints with mypy strict mode

### Out of Scope
- Undo actions (user fixes in Gmail directly)
- Scheduled/cron runs (user runs manually)
- Email search/filtering from CLI (Gmail web is fine)
- Learning/training from user feedback
- PyPI distribution (local use only)
- Email deletion (archive only, labels for bulk delete in Gmail)
- Integration tests

## User Stories

### US-1: First-Time Setup
**Description:** As a new user, I want guided setup so I can configure Google Cloud credentials and add my first account without reading documentation.

**Acceptance Criteria:**
- [ ] Running `python -m gmail_cleaner` with no config shows setup instructions with Google Cloud Console URLs
- [ ] Tool validates credentials.json exists at ~/.gmail-cleaner/credentials.json
- [ ] Tool reports specific error if credentials.json is malformed JSON
- [ ] After credentials validated, prompts "Add your first account?" with account nickname input
- [ ] OAuth browser flow opens when user provides nickname
- [ ] Account token saved to ~/.gmail-cleaner/config.json after successful OAuth
- [ ] If Ollama not running, displays "Ollama not running. Start it now? [Y/n]" and runs `ollama serve` if yes
- [ ] If model not found, displays "Model 'mistral:7b' not found. Install with: ollama pull mistral:7b"
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-2: Add Additional Account
**Description:** As a user with existing setup, I want to add another Gmail account.

**Acceptance Criteria:**
- [ ] "Add account" menu option visible in main menu
- [ ] Selecting it prompts for account nickname (text input)
- [ ] OAuth browser flow opens after nickname entered
- [ ] New account entry added to config.json with email and token
- [ ] New account appears in "Run cleaner (select account)" submenu
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-3: Remove Account
**Description:** As a user, I want to remove a Gmail account from the tool.

**Acceptance Criteria:**
- [ ] "Remove account" menu option shows list of configured accounts
- [ ] Selecting an account shows confirmation: "Remove {email}? [y/N]"
- [ ] Confirming removes account from config.json
- [ ] If only one account exists, shows "Cannot remove last account" and returns to menu
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-4: Run Cleaner - Email Fetching
**Description:** As a user, I want to fetch unprocessed emails from my inbox.

**Acceptance Criteria:**
- [ ] Fetches emails matching: `is:inbox AND NOT label:Auto/Needs-Reply AND NOT label:Auto/Needs-Action AND NOT label:Auto/FYI AND NOT label:Auto/Archive AND NOT label:Auto/Ignore`
- [ ] Processes both read and unread emails (read status ignored)
- [ ] Respects max_emails_per_run setting (default: 100)
- [ ] Shows "Fetching emails from {account}..." during fetch
- [ ] If pending.json exists, prompts "You have pending results. Apply / Discard / Cancel" before fetching
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-5: Run Cleaner - Classification
**Description:** As a user, I want emails classified into categories by the LLM.

**Acceptance Criteria:**
- [ ] Sends emails to Ollama in batches of 5-10
- [ ] Each email sent with: sender, subject, snippet (~200 chars), date
- [ ] LLM returns JSON: `{"category": "...", "reason": "..."}`
- [ ] Valid categories: NEEDS_REPLY, NEEDS_ACTION, FYI, ARCHIVE, IGNORE
- [ ] Invalid JSON response defaults to FYI category
- [ ] Shows progress: "Classifying... [23/47]" updated after each batch
- [ ] If Ollama unreachable, offers to start it or exits with error
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors
- [ ] `pytest tests/test_classifier.py` passes

### US-6: Run Cleaner - Summary Display
**Description:** As a user, I want to see an LLM-generated summary of important emails.

**Acceptance Criteria:**
- [ ] After classification, generates bullet-list summary for: Needs Reply, Needs Action, FYI
- [ ] Each bullet is one-line LLM-generated description of email content
- [ ] Archive and Ignore show count only: "ARCHIVE: 12 emails"
- [ ] Format matches:
  ```
  NEEDS REPLY (3 emails):
  • John wants meeting time for Thursday
  • Boss asked about Q4 project status

  ARCHIVE: 12 emails
  IGNORE: 19 emails
  ```
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-7: Drill-Down and Edit Classifications
**Description:** As a user, I want to review and override individual email classifications before applying.

**Acceptance Criteria:**
- [ ] After summary, shows option: "Drill down into category? [Select or skip]"
- [ ] Selecting a category shows list of emails: sender, subject, current category
- [ ] Arrow keys navigate between emails
- [ ] Enter on email shows options: Change to [other categories] / Skip this email / Back
- [ ] "Skip" marks email to be left untouched (no label, no archive)
- [ ] Changes reflected in pending results before final apply
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-8: Apply Actions to Gmail
**Description:** As a user, I want to apply the classifications to Gmail.

**Acceptance Criteria:**
- [ ] Final prompt shows: "Apply now / Save for later / Discard"
- [ ] "Apply now" creates Auto/* labels in Gmail if they don't exist
- [ ] Applies correct label to each email based on (possibly edited) category
- [ ] Archives emails in ARCHIVE and IGNORE categories (removes from inbox)
- [ ] Skipped emails are not modified
- [ ] Shows completion: "Done. Applied to 47 emails."
- [ ] Deletes pending.json if it existed
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors

### US-9: Save Results for Later
**Description:** As a user, I want to save classification results without applying them immediately.

**Acceptance Criteria:**
- [ ] "Save for later" writes results to ~/.gmail-cleaner/pending.json
- [ ] pending.json contains: created_at timestamp, array of {account, email_id, category, skip, subject, sender}
- [ ] "Apply pending results" menu option appears in main menu when pending.json exists
- [ ] Selecting it applies saved results same as immediate apply
- [ ] After successful apply, pending.json is deleted
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors
- [ ] `pytest tests/test_pending.py` passes

### US-10: Settings Management
**Description:** As a user, I want to configure the tool's behavior.

**Acceptance Criteria:**
- [ ] Settings menu shows: Change model, Customize label names, Max emails per run, Back
- [ ] "Change model" prompts for model name and validates it exists in Ollama
- [ ] "Customize label names" shows current mappings and allows editing each
- [ ] "Max emails per run" prompts for positive integer input
- [ ] Label name changes saved to config.json
- [ ] Label changes apply to new emails only (no migration)
- [ ] `mypy gmail_cleaner/ --strict` passes with no errors
- [ ] `pytest tests/test_config.py` passes

## Technical Design

### Project Structure
```
gmail-cleaner/
├── gmail_cleaner/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── cli.py            # Interactive CLI menus (questionary)
│   ├── gmail.py          # Gmail API wrapper
│   ├── classifier.py     # Ollama integration
│   ├── config.py         # Config file management
│   ├── pending.py        # Pending results management
│   └── types.py          # Type definitions
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_config.py
│   └── test_pending.py
├── pyproject.toml
└── README.md
```

### Data Model

**config.json** (~/.gmail-cleaner/config.json):
```json
{
  "model": "mistral:7b",
  "max_emails_per_run": 100,
  "labels": {
    "NEEDS_REPLY": "Auto/Needs Reply",
    "NEEDS_ACTION": "Auto/Needs Action",
    "FYI": "Auto/FYI",
    "ARCHIVE": "Auto/Archive",
    "IGNORE": "Auto/Ignore"
  },
  "accounts": {
    "personal": {
      "email": "user@gmail.com",
      "token": { "access_token": "...", "refresh_token": "...", ... }
    }
  }
}
```

**pending.json** (~/.gmail-cleaner/pending.json):
```json
{
  "created_at": "2026-02-03T10:00:00Z",
  "results": [
    {
      "account": "personal",
      "email_id": "abc123",
      "category": "NEEDS_REPLY",
      "skip": false,
      "subject": "Meeting Thursday?",
      "sender": "john@example.com"
    }
  ]
}
```

### Gmail API Scopes
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.labels`

### LLM Prompts

**Classification prompt:**
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

**Summary prompt:**
```
Summarize these emails in a bullet list. Each bullet should be one short sentence describing what the email is about.

Emails:
{list of subject + sender + snippet}

Respond with bullet points only, one per email.
```

## Functional Requirements

- FR-1: Support 3 Gmail accounts with identical classification rules
- FR-2: OAuth 2.0 authentication with persistent token storage in ~/.gmail-cleaner/config.json
- FR-3: Classify emails into 5 categories (NEEDS_REPLY, NEEDS_ACTION, FYI, ARCHIVE, IGNORE) using local Ollama LLM
- FR-4: Apply Gmail labels automatically based on classification with Auto/* prefix
- FR-5: Archive emails in ARCHIVE and IGNORE categories (remove from inbox, keep labeled)
- FR-6: Generate LLM bullet-list summaries for NEEDS_REPLY, NEEDS_ACTION, FYI categories
- FR-7: Allow drill-down to view individual emails and override category or skip
- FR-8: Support saving classification results to pending.json for later application
- FR-9: Configurable label names, Ollama model, and max emails per run via Settings menu
- FR-10: Skip emails that already have any Auto/* label (Gmail labels are source of truth)
- FR-11: Prompt to handle pending results before starting new classification run
- FR-12: Offer to start Ollama if not running when needed

## Non-Functional Requirements

- NFR-1: All code must pass `mypy gmail_cleaner/ --strict` with no errors
- NFR-2: Unit tests must exist for classifier.py, config.py, and pending.py
- NFR-3: Process emails in batches of 5-10 per Ollama request
- NFR-4: Default max 100 emails per run (configurable)
- NFR-5: Invalid LLM JSON responses default to FYI category (safe fallback)
- NFR-6: All external API calls (Gmail, Ollama) must be mockable for testing

## Implementation Phases

### Phase 1: Foundation & Config
- [ ] Initialize Python project with pyproject.toml (dependencies: google-api-python-client, google-auth-oauthlib, ollama, questionary)
- [ ] Create project structure with all module files
- [ ] Implement types.py with dataclasses/TypedDicts for config, pending, email data
- [ ] Implement config.py: load/save config, validate structure, default values
- [ ] Implement guided setup flow in cli.py (credentials check, first account prompt)
- [ ] Write tests/test_config.py with mocked file I/O
- **Verification:** `mypy gmail_cleaner/ --strict && pytest tests/test_config.py`

### Phase 2: Gmail Integration
- [ ] Implement gmail.py: OAuth flow, token storage/refresh, service creation
- [ ] Implement email fetching with label exclusion query
- [ ] Implement label creation (create Auto/* labels if not exist)
- [ ] Implement label application and archive actions
- [ ] Add account management (add/remove) to cli.py
- **Verification:** `mypy gmail_cleaner/ --strict && pytest`

### Phase 3: Classification & Summary
- [ ] Implement classifier.py: Ollama connection, batch processing, JSON parsing
- [ ] Implement classification prompt template
- [ ] Implement summary generation for NEEDS_REPLY, NEEDS_ACTION, FYI
- [ ] Implement FYI fallback for invalid JSON responses
- [ ] Implement Ollama health check and offer to start
- [ ] Write tests/test_classifier.py with mocked Ollama responses
- **Verification:** `mypy gmail_cleaner/ --strict && pytest tests/test_classifier.py`

### Phase 4: CLI & Pending Results
- [ ] Implement main menu with questionary (Run, Add/Remove account, Settings, Exit)
- [ ] Implement run flow: fetch → classify → summarize → display → final prompt
- [ ] Implement drill-down view with category override and skip
- [ ] Implement pending.py: save/load pending results, apply pending
- [ ] Implement settings menu (model, labels, max emails)
- [ ] Write tests/test_pending.py with mocked file I/O
- [ ] Implement "Apply pending results" menu option (shown when pending.json exists)
- **Verification:** `mypy gmail_cleaner/ --strict && pytest`

## Definition of Done

This feature is complete when:
- [ ] All user story acceptance criteria pass
- [ ] All implementation phases verified
- [ ] Tests pass: `pytest`
- [ ] Type check passes: `mypy gmail_cleaner/ --strict`
- [ ] Tool runs end-to-end with real Gmail account (manual verification)

## Ralph Loop Command

```bash
/ralph-loop "Implement Gmail Cleaner CLI per spec at docs/specs/usersshantamgmail-cleanerdocsplans2026-02-03-gmail-cleaner-designmd.md

PHASES:
1. Foundation & Config: pyproject.toml, types.py, config.py, guided setup - verify with mypy gmail_cleaner/ --strict && pytest tests/test_config.py
2. Gmail Integration: gmail.py OAuth flow, email fetching, labels, archive - verify with mypy gmail_cleaner/ --strict && pytest
3. Classification & Summary: classifier.py, Ollama integration, batch processing, summaries - verify with mypy gmail_cleaner/ --strict && pytest tests/test_classifier.py
4. CLI & Pending: cli.py menus, run flow, drill-down, pending.py, settings - verify with mypy gmail_cleaner/ --strict && pytest

VERIFICATION (run after each phase):
- mypy gmail_cleaner/ --strict
- pytest

ESCAPE HATCH: After 20 iterations without progress:
- Document what's blocking in the spec file under 'Implementation Notes'
- List approaches attempted
- Stop and ask for human guidance

Output <promise>COMPLETE</promise> when all phases pass verification." --max-iterations 30 --completion-promise "COMPLETE"
```

## Open Questions

None - all questions resolved during interview.

## Implementation Notes

*To be filled during implementation.*

---

<promise>SPEC COMPLETE</promise>
