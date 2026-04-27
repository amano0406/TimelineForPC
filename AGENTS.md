# AGENTS.md

## Repo purpose

This repository is `TimelineForPC`.
Its job is to capture the current state of a Windows PC and export one readable local artifact without turning into a broad activity-tracking platform.

## Must preserve

- Keep the product local-first and CLI-first.
- Do not add a web UI unless explicitly requested.
- Do not delete, overwrite, mass-move, or mass-rename user files.
- Keep mock mode stable. It is part of the product contract.
- Preserve the current output contract and the default output root behavior unless explicitly approved.
- Prefer fixed output/state roots by default rather than arbitrary ad-hoc path workflows.

## Product-specific guardrails

- Preserve `request.json`, `status.json`, `result.json`, `manifest.json`, `snapshot.json`, `snapshot_redacted.json`, `report.md`, and `export/*`.
- Keep redaction behavior explicit and documented.
- Avoid turning this repo into continuous screenshot/video/activity capture without explicit approval. That is a different product scope.
- Keep dependencies minimal. If a new production dependency is necessary, document the reason in the README.

## Standard model

```text
InputSource = the local machine or mock profile used for capture
InputItem   = the captured machine snapshot scope
Job         = the capture request and selected redaction/profile
Run         = one execution attempt for that capture
Artifact    = exported report and structured snapshot outputs
```

## Safe work without extra confirmation

- read-only investigation
- `AGENTS.md`, README, docs, and `.env.example` updates
- non-destructive small code fixes
- test and mock-mode maintenance
- output contract consistency fixes that do not remove user data

## Ask before doing these

- deleting or rewriting user data
- breaking mock mode
- breaking output contract changes
- repo or product rename
- new hosted/cloud dependency
- deploy, external posting, or secret changes
- expanding scope into continuous activity logging

## Before finishing

- Read the README first.
- Keep `python -m pytest` passing when code behavior changes.
- Update docs when defaults, redaction, or output behavior changes.

## Report format

```md
## Current state
## Completed
## Changed files
## Tests
## Risks
## Next safe tasks
## Human decisions needed
```
