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

## Sources (v1, built and tested against live sites)

| Beat | Source | Fetch method |
|---|---|---|
| AI | arXiv cs.AI, cs.CL | Official API |
| AI | OpenAI blog | RSS — `openai.com/news/rss.xml` |
| AI | Google DeepMind blog | RSS — `deepmind.google/blog/feed/basic/` |
| AI | Latent Space | RSS — `latent.space/feed` (Substack) |
| AI | Anthropic news | Scraping — no official RSS feed exists |
| AI | Anthropic Research | Scraping — no RSS; same page structure as Anthropic news |
| Design | Nielsen Norman Group | RSS — `nngroup.com/feed/rss` |
| Design | Smashing Magazine | RSS — `smashingmagazine.com/feed/` |
| Design | UX Collective | RSS — `uxdesign.cc/feed` (Medium-backed) |
| Voice AI | Deepgram blog | RSS — `deepgram.com/blog.xml` (confirmed working; feedparser must fetch via `requests` with browser headers first, not parse the URL directly, or Deepgram's server returns malformed XML) |
| Voice AI | ElevenLabs blog | Scraping — no RSS feed found |
| Voice AI | Rain.agency | Scraping — actual path is `/insights-updates/`, not `/blog` |
| Voice AI | Rasa blog | Scraping — no RSS feed found |

8 of 12 sources use free, official RSS — reliable, low maintenance. The 4 scraped sources (Anthropic news + Research, ElevenLabs, Rain.agency, Rasa) are more fragile: a site redesign can silently break the scraper until noticed and fixed. Budget for occasional maintenance there.

**Dropped after testing:** VoiceBot.ai (RSS confirmed genuinely stale — stuck at ~2 years old content despite returning valid 200 responses), Voice & AI / voiceand.ai (domain doesn't resolve), Google PAIR and Stanford AI Index (both evergreen/annual publications with no dated posts — structurally incompatible with a 24h-window digest), OpenAI Research (the `/research/` page blocks scraping outright, and the existing OpenAI news RSS already mixes in research content), The Batch (no RSS feed exists despite search results suggesting one; weekly cadence made a scraper not worth building).

**Fetch behavior note:** several sources (VoiceBot.ai in particular) sit behind Cloudflare bot protection and reject a self-identifying bot User-Agent — the fetcher uses a standard browser UA string throughout.

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

**Web search fallback (added after real-world testing, deviation from original "no tool-calling" framing):** if a beat's curated sources return 0 candidates for the day, one bounded Tavily search (`topic: news`, `search_depth: advanced`, `time_range: day`) runs before giving up, and its results feed into the same ranking/summarization call rather than showing empty. This is still deterministic — one search, one summarize, no loops, no autonomous multi-step decision-making — just a wider net for the specific case where the curated source list came up dry. Tavily's free tier (1,000 search credits/month, no card required) covers this comfortably; Gemini's own Google Search grounding was tested first and found to require billing enabled even on a free-tier key, so it wasn't used. Items found this way cite the actual source domain from the search result, same as curated items — no visual distinction on the site. (Default `topic`/`search_depth` gave noticeably worse results in testing — a movie trailer and an unrelated podcast came back for a "voice AI news" query — the `news` topic + `advanced` depth combination fixed this.)

**LLM provider fallback:** if the Gemini call itself fails (outage, rate limit), the same prompt retries once against Qwen3.6-27B via Groq's free tier (no card, `qwen/qwen3.6-27b`) before giving up on that beat. Groq's free tier caps at 8,000 tokens/minute for this model, which is tight for a reasoning model that spends tokens thinking before answering — confirmed by testing that the default token budget silently truncates before valid JSON is produced (`json_validate_failed` with an empty `failed_generation`). Fixed with an explicit `max_completion_tokens: 4000`. In a worst case where Gemini fails for all 3 beats in one run, the Groq fallback could itself hit that per-minute ceiling on the 2nd or 3rd beat — acceptable given how rare a full-Gemini-outage day would be; that beat just falls back to its normal empty-state behavior rather than crashing the run.

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
- **Gemini Flash-Lite** — combined ranking + summarization call, via the raw REST API (`generateContent` with `responseSchema` for structured JSON output — no SDK dependency). Model ID as of build time: `gemini-3.5-flash-lite` (the `2.5` version was deprecated for new users mid-build — re-verify the current ID if `generateContent` starts 404ing). Free tier (1,000 requests/day, 15 RPM) comfortably covers the ~3 calls/day this needs, indefinitely. Beats with 0 fetched candidates skip the API call entirely.
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
- Zero-qualifying-items case — **confirmed:** show fewer than 2-3 for that beat, don't force-fill with filler. Validated in practice: a real `fetch.py` run against all 12 live sources returned 0 items for the entire Voice AI beat on a normal day — most sources simply don't publish daily, which is expected, not a bug.
- Deepgram and Rain.agency's fetch targets — **resolved:** both confirmed working (Deepgram needed a header fix, Rain.agency's real path is `/insights-updates/`)
- Full visual/UX system, layout, content budget rationale, and data viz scope — see `design.md`
