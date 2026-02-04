# Specification Draft: /Users/shantam/gmail-cleaner/docs/plans/2026-02-03-gmail-cleaner-design.md

*Interview in progress - Started: 2026-02-03*

## Overview
[To be filled during interview]

## Problem Statement
[To be filled during interview]

## Scope

### In Scope
<!-- Explicit list of what IS included in this implementation -->
- [To be filled during interview]

### Out of Scope
<!-- Explicit list of what is NOT included - future work, won't fix, etc. -->
- [To be filled during interview]

## User Stories

<!--
IMPORTANT: Each story must be small enough to complete in ONE focused coding session.
If a story is too large, break it into smaller stories.

Format each story with VERIFIABLE acceptance criteria:

### US-1: [Story Title]
**Description:** As a [user type], I want [action] so that [benefit].

**Acceptance Criteria:**
- [ ] [Specific, verifiable criterion - e.g., "API returns 200 for valid input"]
- [ ] [Another verifiable criterion - e.g., "Error message displayed for invalid email"]
- [ ] Typecheck/lint passes
- [ ] [If UI] Verify in browser

BAD criteria (too vague): "Works correctly", "Is fast", "Handles errors"
GOOD criteria: "Response time < 200ms", "Returns 404 for missing resource", "Form shows inline validation"
-->

[To be filled during interview]

## Technical Design

### Data Model
[To be filled during interview]

### API Endpoints
[To be filled during interview]

### Integration Points
[To be filled during interview]

## User Experience

### User Flows
[To be filled during interview]

### Edge Cases
[To be filled during interview]

## Requirements

### Functional Requirements
<!--
Use FR-IDs for each requirement:
- FR-1: [Requirement description]
- FR-2: [Requirement description]
-->
[To be filled during interview]

### Non-Functional Requirements
<!--
Performance, security, scalability requirements:
- NFR-1: [Requirement - e.g., "Response time < 500ms for 95th percentile"]
- NFR-2: [Requirement - e.g., "Support 100 concurrent users"]
-->
[To be filled during interview]

## Implementation Phases

<!-- Break work into 2-4 incremental milestones Ralph can complete one at a time -->

### Phase 1: [Foundation/Setup]
- [ ] [Task 1]
- [ ] [Task 2]
- **Verification:** `[command to verify phase 1]`

### Phase 2: [Core Implementation]
- [ ] [Task 1]
- [ ] [Task 2]
- **Verification:** `[command to verify phase 2]`

### Phase 3: [Integration/Polish]
- [ ] [Task 1]
- [ ] [Task 2]
- **Verification:** `[command to verify phase 3]`

<!-- Add Phase 4 if needed for complex features -->

## Definition of Done

This feature is complete when:
- [ ] All acceptance criteria in user stories pass
- [ ] All implementation phases verified
- [ ] Tests pass: `[verification command]`
- [ ] Types/lint check: `[verification command]`
- [ ] Build succeeds: `[verification command]`

## Ralph Loop Command

<!-- Generated at finalization with phases and escape hatch -->

```bash
/ralph-loop "Implement /Users/shantam/gmail-cleaner/docs/plans/2026-02-03-gmail-cleaner-design.md per spec at docs/specs/usersshantamgmail-cleanerdocsplans2026-02-03-gmail-cleaner-designmd.md

PHASES:
1. [Phase 1 name]: [tasks] - verify with [command]
2. [Phase 2 name]: [tasks] - verify with [command]
3. [Phase 3 name]: [tasks] - verify with [command]

VERIFICATION (run after each phase):
- [test command]
- [lint/typecheck command]
- [build command]

ESCAPE HATCH: After 20 iterations without progress:
- Document what's blocking in the spec file under 'Implementation Notes'
- List approaches attempted
- Stop and ask for human guidance

Output <promise>COMPLETE</promise> when all phases pass verification." --max-iterations 30 --completion-promise "COMPLETE"
```

## Open Questions
[To be filled during interview]

## Implementation Notes
[To be filled during interview]

---
*Interview notes will be accumulated below as the interview progresses*
---

## Interview Notes

### Processing Strategy
- **Batch processing**: Send emails to Ollama in batches of 5-10 for optimal speed
- Progress updates shown after each batch completes

### Email Scope
- **All inbox emails**: Process all emails in inbox that don't have an Auto/* label
- Read/unread status is ignored - if it's in inbox without a label, process it
- This ensures emails the user has glanced at but not acted on still get categorized

### Dry Run Mode - Key Insight
- Dry run should show proposed classifications
- **Key feature**: Allow saving dry-run results and applying them later without re-processing
- Flow: dry-run → review → apply (or discard)
- Avoids wasting LLM processing time if user likes the results
- **Persistence**: Results stored in ~/.gmail-cleaner/pending.json (persists across sessions)
- **Conflict handling**: If pending results exist when running cleaner, prompt user to apply or discard first

### Re-classification Behavior
- If user manually removes an Auto/* label from an email, it will be re-classified on next run
- No local tracking of processed IDs - Gmail labels are the source of truth
- This allows users to "reset" an email's classification if they disagree

### Batch Limits
- Configurable max emails per run (default: 100)
- Stored in settings
- Prevents runaway processing on first run with large inbox

### No Learning/Training
- Keep it simple - rely on the LLM prompt only
- No sender rules, no feedback loop
- User can manually fix misclassifications in Gmail

### Ollama Error Handling
- If Ollama not running: Offer to start it (`ollama serve` in background)
- If model not found: Show install command and exit

### Settings Menu
- Change Ollama model
- Customize label names (e.g., 'Auto/Needs Reply' → 'Action/Reply')
- Change max emails per run
- Label changes apply to NEW emails only (no migration of existing)

### Out of Scope (v1)
- Undo actions (user fixes in Gmail directly)
- Scheduled/cron runs (user runs manually)
- Email search/filtering from CLI (Gmail web is fine for this)

### Simplified Menu (Dry-run merged into Run)
- Remove separate "Dry run" option
- Single "Run cleaner" flow that always shows summary first
- Menu becomes:
  ```
  Gmail Cleaner
  ─────────────
  ❯ Run cleaner (all accounts)
    Run cleaner (select account)
    ─────────────
    Apply pending results (if any)
    ─────────────
    Add account
    Remove account
    Settings
    ─────────────
    Exit
  ```

### Run Flow - LLM Summaries
- After classification, generate LLM summary for: Needs Reply, Needs Action, FYI
- Archive and Ignore do NOT get summaries (just counts)
- Format: Bullet list per category
  ```
  NEEDS REPLY (3 emails):
  • John wants meeting time for Thursday
  • Boss asked about Q4 project status
  • Client requesting invoice update

  NEEDS ACTION (2 emails):
  • Approve expense report from Sarah
  • Sign DocuSign document from Legal

  FYI (5 emails):
  • Weekly newsletter from Dev Weekly
  • GitHub notification: PR merged
  • ...

  ARCHIVE: 12 emails
  IGNORE: 19 emails
  ```

### Drill-Down Feature
- After summary, user can drill into any category
- Per email: can override category OR mark "skip" (leave untouched)
- Navigate with arrows, select with Enter

### Final Prompt
After summary (and optional drill-down edits):
```
❯ Apply now
  Save for later
  Discard
```
- Apply now: Apply labels + archive actions to Gmail
- Save for later: Store to ~/.gmail-cleaner/pending.json
- Discard: Throw away results, no changes made

### Testing Strategy
- Unit tests for core logic (classifier parsing, config handling, label mapping)
- Mock external APIs (Gmail, Ollama)
- No integration tests for v1
- Framework: pytest

### Type Checking
- Full type hints on all functions
- mypy strict mode
- Run with: `mypy gmail_cleaner/`

### Distribution
- Local use only (not deploying to PyPI)
- Run with: `python -m gmail_cleaner` from repo root
- Dependencies managed via pyproject.toml + pip install -e .

