# AI24 — PRD

**One-liner:** Automated daily digest of the most important AI, Design, and Voice AI updates from the past 24 hours, published to a personal newsletter-style website by 9 AM, with a push notification linking straight to it. Also serves as a portfolio piece demonstrating AI-native product/design/build skills — see design.md for the full visual/UX system.

---

## System Type

**Workflow, not agent** (per Anthropic's "Building Effective Agents" framing). Fixed, deterministic pipeline run once a day — no ambiguous multi-step decision-making, no tool-calling loops. Keep it boring and reliable.

**Pipeline:**
`Fetch → Filter (24h) → Rank & select top 2-3/beat → Summarize (what/why/how) → Generate page + update archive → Deploy → Push notification`

---

## v1 Scope

### In scope
- 3 beats: **AI**, **Design**, **Voice AI**
- 2-3 top items per beat per day (target ~6-9 items total, no hard cap, curated hard)
- Runs once daily, published by 9 AM IST
- Single delivery channel: website + push notification
- Rolling archive of all past digests
- Portfolio-grade visual design — this project doubles as a demonstration piece for "AI builder" job applications, so build quality and craft matter beyond personal use

### Out of scope (v1)
- Additional beats beyond the 3 (design should allow adding later, not building it now)
- Community-signal ranking (HN/Reddit upvotes, virality) — not used to select items
- Multi-channel delivery (no Slack, no email)
- Search/tagging/filtering within the archive — reverse-chronological list with prev/next-day navigation
- Personalization or feedback loop (no thumbs up/down, no learning from what you read)
- Per-item ranking-score visualization (radar/bar of source authority/relevance/novelty) — considered, kept out to keep item cards clean; may revisit later

---

## Sources (v1, verified)

| Beat | Source | Fetch method |
|---|---|---|
| AI | arXiv cs.AI, cs.CL | Official API/RSS |
| AI | OpenAI blog | RSS — `openai.com/news/rss.xml` |
| AI | Google DeepMind blog | RSS — `deepmind.google/blog/feed/basic/` |
| AI | Anthropic blog | Scraping — no official RSS feed exists |
| Design | Nielsen Norman Group | RSS — `nngroup.com/feed/rss` |
| Design | Smashing Magazine | RSS — `smashingmagazine.com/feed/` |
| Design | UX Collective | RSS — `uxdesign.cc/feed` (Medium-backed) |
| Voice AI | VoiceBot.ai | RSS — `voicebot.ai/feed/` (verified live) |
| Voice AI | Deepgram blog | RSS — `deepgram.com/blog.xml` (re-verify at build time; blog URL structure looked inconsistent during research) |
| Voice AI | ElevenLabs blog | Scraping — no RSS feed found |
| Voice AI | Rain.agency blog | Scraping — no RSS found, site had redirect/404 issues during research; re-verify it's still active at build time |

7 of 10 sources use free, official RSS — reliable, low maintenance. The 3 scraped sources (Anthropic, ElevenLabs, Rain.agency) are more fragile: a site redesign can silently break the scraper until noticed and fixed. Budget for occasional maintenance there.

**Note:** HN/Reddit dropped from v1 — community engagement wasn't picked as a ranking factor, so including them adds complexity without a clear use.

---

## Filtering & Ranking Logic

1. Fetch latest items from each source.
2. Filter to items published in the last 24 hours.
3. **One combined Gemini Flash-Lite call per beat** (not separate rank + summarize steps). Each call receives:
   - All candidate items for that beat (title + snippet/abstract + source)
   - The user's personalization blurb (below)
   - The last 2-3 days of previously-published items, read directly from the archive JSON files already present in the GitHub Actions checked-out repo (no separate storage needed — the site's own archive is the pipeline's dedup memory)
   - and returns the top 2-3 picks **with their summaries already written**, as structured JSON, in one call.
4. Ranking criteria (combined, not strict order):
   - Source authority (major labs / top publications)
   - Relevance to the user's work (per the blurb below)
   - Novelty (genuinely new, not incremental; deprioritize stories already covered in the last 2-3 days)
   - **Tie-break rule:** practical/try-able items (tools, APIs, launches you can actually use) outrank prestigious-but-theoretical research when scores are otherwise close.
5. ~3 API calls/day total (one per beat) — trivially within Gemini Flash-Lite's free tier (1,000 requests/day, 15 RPM, 250k TPM).

**Personalization blurb (baked into the ranking prompt):**
> "I'm targeting 'AI builder' roles — doing product management, product design, and development myself using AI tools, with no handoffs between those functions. I'm hands-on building a voice agent right now and believe voice is the next major interface paradigm, so I want to stay aggressively current on anything I can actually try or apply — new tools, techniques, and patterns — not just read about. Prioritize practical/actionable developments over pure research unless a paper has clear, immediate product implications."

---

## Summarization Approach

- **Structure per item:** What happened → Why it matters → How it impacts your work
- **Tone:** straight, gist-style, high information density — no filler, no long paragraphs
- **Content budget** (soft target, not a rigid per-line cap):
  - Headline: ≤70 characters
  - What / Why / Your work: soft target ~100-150 characters each (1-2 sentences)
  - Hard truncation ceiling (~220-250 characters) enforced in code as a safety net for outliers only — guarantees the layout never breaks on unusually long model output, without aggressively chopping normal sentences
- **Citation:** single source per item (no multi-source merging across outlets covering the same story) — rendered as a publisher-name chip (e.g. "OpenAI ↗") linking directly to the source article
- **Length target:** skimmable in under 2 minutes across all beats combined (~600 words total at 9 items)

---

## Delivery

- **Format:** custom site (Astro), replaces Notion as destination entirely
- **Hosting:** Vercel (free Hobby tier), auto-deploys on every git push
- **Data storage:** one immutable JSON file per day (`/data/digests/YYYY-MM-DD.json`), committed to the repo — any archive date always renders exactly what was published that day, nothing gets overwritten or regenerated later
- **Structure:**
  - Homepage = the **latest available digest** (see failure fallback below), not hard-coded to "today"
  - Individual day pages with prev/next-day navigation (not just a bounce back to the archive list each time)
  - Archive = full reverse-chronological list of all past days
- **Homepage failure fallback:** if a day's pipeline run fails or produces nothing, the homepage still shows the newest file that actually exists (never blank/broken) — but a visible banner surfaces the gap: *"Today's digest didn't publish — showing [date]'s digest."* Graceful degradation plus honest transparency.
- **Notification:** push via [ntfy.sh](https://ntfy.sh) (free, no signup), triggered after the pipeline pushes new content and Vercel finishes deploying — replaces the original Hammerspoon plan (see Tech Stack below for why).
- **Full visual/UX design system:** see `design.md`

---

## Tech Stack (updated — fully free tier)

- **Python** — fetch, filter, ranking orchestration
- **Gemini Flash-Lite** — combined ranking + summarization call. Free tier (1,000 requests/day, 15 RPM) comfortably covers the ~3 calls/day this needs, indefinitely
- **Astro** — static site generator. Chosen over Next.js for this project: content-driven (a handful of structured JSON files → templated pages), ships close to zero JS, fast builds — nothing here needs React's client-side machinery
- **Vercel** — hosting (free Hobby tier), replaces Notion API for this project
- **GitHub Actions (cron)** — daily pipeline execution, **replaces Hammerspoon**. Free (unlimited minutes on a public repo), and doesn't depend on the local Mac being awake and unlocked at 9 AM — a real reliability risk for the original local-only plan.
  - Caveat: GitHub Actions cron runs in UTC and isn't minute-precise — "9 AM IST" (3:30 AM UTC) may occasionally slip by several minutes under load. Fine for a personal tool; worth setting expectations rather than promising an exact time.
- **ntfy.sh** — push notification, **replaces Hammerspoon** (which only works if the pipeline runs locally; moving pipeline execution to GitHub Actions means the notification path had to move too)

---

## Success Criteria

Working if, after 2-3 weeks of use:
- It saves time vs. manually browsing sources
- You can speak to recent developments in interviews/conversations
- You actually open and read it most mornings

No hard numeric target for v1 — self-assessed.

---

## Open Questions / Assumptions to confirm before build

- Timezone for 9 AM — **confirmed IST (Kollam)**
- Zero-qualifying-items case — **confirmed:** show fewer than 2-3 for that beat, don't force-fill with filler
- Deepgram blog and Rain.agency's RSS/scraping targets showed some inconsistency during research (URL structure, redirects/404s) — re-verify both are still live and correct at build time
- Full visual/UX system, layout, content budget rationale, and data viz scope — see `design.md`
