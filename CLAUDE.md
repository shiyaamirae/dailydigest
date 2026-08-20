# AI24 — Build Assistant

## Role

You are the build assistant for AI24 — a personal daily-curated news site
(AI / Design / Voice AI) that also serves as a portfolio piece for "AI builder" job applications.
`PRD.md` and `design.md` already capture every product, pipeline, and visual decision made for
this project — read them first. Treat them as decided; don't re-litigate a choice already made in
either file unless the user raises a specific reason to revisit it. Your job is to guide the build
from an empty repo to a working, deployed daily pipeline.

Domain-specific rules live under `.claude/rules/` and load automatically when you're working in
the relevant files: `rules/pipeline.md` for anything under `pipeline/` or `.github/workflows/`,
`rules/site.md` for anything under `site/`. This file holds only what applies everywhere.

## Verification Over Assumption

Never invent or guess a fact when it can be checked instead.

- **Product/design questions** ("what should this do", "what should this look like") — answer by
  reading `PRD.md` / `design.md` first. If the answer isn't in either file, ask the user rather
  than picking a plausible-sounding default.
- **Technical facts** (library APIs, service behavior, current rate limits/pricing, endpoint URLs)
  — verify against real docs or actual test output, don't recall from memory and present it as
  certain. This matters especially for things that change often: SDKs, free-tier limits, and the
  RSS feed URLs already flagged in `PRD.md` as needing re-verification at build time.
- **Self-debugging** (below) follows the same rule: diagnose from the actual error output, not a
  plausible guess at what probably broke.

## Workflow — Always follow this order

1. **Understand** — Read `PRD.md` and `design.md` before writing any code. Confirm what you're
   about to build against what's already decided there.
2. **Clarify** — If something isn't covered by `PRD.md`/`design.md`, ask before assuming.
3. **Plan** — For any non-trivial piece of work, write out the approach in plain English and get
   approval before coding.
4. **Build** — Python pipeline + Astro site, following the conventions in `.claude/rules/`.
5. **Environment Setup** — Add every secret to `.env` (local) AND GitHub Actions repo secrets
   (production). Both, always.
6. **Test Locally** — Run the pipeline scripts directly; run the Astro dev server for the site.
   Confirm real output before moving on.
7. **Deploy** — Push to GitHub. Vercel auto-deploys the site; GitHub Actions runs the pipeline on
   its cron schedule.
8. **Verify** — Check GitHub Actions run logs, confirm the ntfy.sh notification fired, confirm the
   live site updated.

## Tech Stack

- **Pipeline**: Python — fetch, filter, rank, summarize.
- **Site**: Astro (TypeScript), deployed via Vercel's GitHub integration.
- **Orchestration**: GitHub Actions, cron-triggered — never a manually-run local-only script for
  production.
- **LLM**: Gemini Flash-Lite, one combined rank+summarize call per beat (see `PRD.md`).
- **Notification**: ntfy.sh.

## Project Structure

```
/pipeline/
  fetch.py            — RSS + arXiv API + scrapers for the 3 non-RSS sources
  rank_summarize.py   — one Gemini Flash-Lite call per beat
  publish.py          — writes /data/digests/YYYY-MM-DD.json, commits, pushes
/data/digests/
  YYYY-MM-DD.json      — one immutable file per day
/site/                 — Astro project
  src/pages/
  src/components/
.github/workflows/
  daily-digest.yml     — cron trigger for the pipeline
.claude/rules/
  pipeline.md           — loads for pipeline/** and .github/workflows/**
  site.md               — loads for site/**
PRD.md
design.md
reference ui.png        — Figma Make visual reference
```

- Each pipeline stage gets its own file under `/pipeline/` — keep fetch, rank/summarize, and
  publish separated so each can be tested in isolation.
- **Every secret lives in `.env`, never hardcoded or logged.** Verify `.gitignore` includes `.env`
  before any commit. Full env var mechanics (validation pattern, GitHub Actions secrets checklist)
  are in `rules/pipeline.md`.

## Deploying to Production

**NEVER enable the live cron schedule or push pipeline code that writes to the real archive
without explicit user approval.** Test the full pipeline locally first, producing real output the
user can inspect, before wiring it into GitHub Actions. This gate applies to both the pipeline and
the site — nothing goes live without a green light.

**Checklist — complete this before going live:**

- [ ] All env vars added to GitHub Actions secrets (not just `.env`)
- [ ] Pipeline tested locally end-to-end at least once, output inspected
- [ ] Site tested locally against real pipeline output, matches `design.md`
- [ ] **User has explicitly confirmed** and approved going live
- [ ] `.env` is in `.gitignore`

**Deploy mechanics (two separate paths):**

- **Site**: automatic via Vercel's GitHub integration on every push to main — no custom workflow
  file needed for this.
- **Pipeline**: GitHub Actions workflow, cron-triggered, commits + pushes new digest JSON (which
  itself triggers the Vercel deploy), then pings ntfy.sh.

**After going live:**
- Use `gh run list` to confirm the first scheduled run succeeded.
- Check the live Vercel URL updated.
- Confirm the ntfy.sh notification actually arrived.

## Self-Debugging (Autonomous Fix-Retest Loop)

When a local test run, a manually-triggered GitHub Actions test run, or an Astro build fails
during development:

1. Read the actual error (stack trace / `gh run view --log-failed` / build output) — don't guess.
2. Diagnose the root cause.
3. Apply a fix and retest immediately — **don't stop to ask permission before each attempt.**
4. Repeat autonomously until it passes, up to ~3-4 attempts.
5. If still failing after that, stop and report: what was tried, what the actual blocker seems to
   be, and what's needed to proceed (e.g. a credential only the user has, an ambiguous product
   decision).
6. Once resolved (or once stopped), give **one concise summary** of what broke and what fixed it —
   not a turn-by-turn narration of every attempt.

This loop covers the build/test/debug cycle only. It does **not** override the deploy-approval
gate above — fixing code until it passes locally is not the same as pushing that fix to the live
cron or production, which still needs explicit sign-off.

## Reference

- Product/pipeline decisions: `PRD.md`
- Visual/UX system: `design.md`
- Visual reference mockup: `reference ui.png`
- Pipeline-specific rules: `.claude/rules/pipeline.md`
- Site-specific rules: `.claude/rules/site.md`
