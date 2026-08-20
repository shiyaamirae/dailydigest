---
paths:
  - "pipeline/**/*.py"
  - ".github/workflows/**"
---

# Pipeline & GitHub Actions Rules

## Environment Variables — Security Rules

- **Every secret lives in `.env`** — `GEMINI_API_KEY`, `NTFY_TOPIC`, and anything else a source
  scraper might eventually need. No exceptions.
- **Never log secret values** — `print("Key:", api_key)` is a security violation.
- **Never hardcode credentials** — not even temporarily, not even in comments.
- **Always validate at the top of every script**:
  ```python
  import os

  api_key = os.environ.get("GEMINI_API_KEY")
  if not api_key:
      raise RuntimeError("GEMINI_API_KEY is not set")
  ```
- **Production target is GitHub Actions repo secrets**, not a dashboard — before enabling the live
  cron: GitHub → repo → Settings → Secrets and variables → Actions. This is the #1 cause of
  production pipeline failures.
- **When adding a new env var**: add it to `.env` with a comment on where to get it, then remind
  the user to add it to GitHub Actions secrets too.

## GitHub Actions Critical Rules

- Cron runs in **UTC** and is not minute-precise. 9 AM IST = `30 3 * * *`; a run can slip by
  several minutes under load (documented in `PRD.md` — don't promise an exact publish time).
- The workflow needs **`contents: write`** permission (or a PAT) to commit the new digest JSON
  back to the repo — a default `GITHUB_TOKEN` push needs this explicitly granted.
- Fetch/scrape steps should **fail gracefully per-source** (log and skip) rather than crashing the
  whole run — one broken scraper (Anthropic / ElevenLabs / Rain.agency) shouldn't take down the
  other 9 sources.
- Set a job timeout (e.g. 10 minutes) so a hung request doesn't burn Actions minutes indefinitely.

## Scheduling

```yaml
on:
  schedule:
    - cron: "30 3 * * *"   # 9:00 AM IST
  workflow_dispatch: {}     # always keep this enabled for manual test runs
```

Always ask the user before changing the schedule. Keep `workflow_dispatch` enabled so a run can be
fired manually for testing without waiting for the cron.

## CLI Tools — Use These for Verification

No MCP automation tool is wired up for this stack — use `gh` CLI directly:

| What you need to do | Command |
|---|---|
| Fire a manual pipeline run | `gh workflow run daily-digest.yml` |
| List recent runs | `gh run list --workflow=daily-digest.yml` |
| Read logs for a run | `gh run view <run-id> --log` |
| Check a specific job's failure | `gh run view <run-id> --log-failed` |

## Testing Locally

1. Run `python pipeline/fetch.py`, then `python pipeline/rank_summarize.py` directly — inspect the
   output JSON before wiring up `publish.py`'s commit/push step.
2. **Never exercise the real commit/push/notify path without saying so explicitly** — use a
   dry-run flag or a scratch branch first.

## When a Run Fails

1. `gh run view <run-id> --log-failed` for the error.
2. Most common causes specific to this project:
   - **Missing secret in GitHub Actions** — present in `.env` locally, never added to repo secrets
   - **A scraped source changed its HTML structure** (Anthropic / ElevenLabs / Rain.agency) —
     scraper needs updating
   - **Gemini returned malformed JSON** — check the structured-output schema/prompt
   - **Character-budget truncation producing odd output** — check the hard-ceiling logic
   - **Git push conflict** — a manual run overlapped with the scheduled one
3. Fix, test locally again, then re-run.

## Adding Packages

```bash
pip install {package}          # add to requirements.txt / pyproject.toml
```
