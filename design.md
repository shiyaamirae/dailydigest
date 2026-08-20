# AI24 — Design System

## Identity

**"A field notebook / research journal kept by an AI builder."**

Two registers layered deliberately:
- **Mono UI chrome** (navigation, dates, labels, citations) — reads as typewritten marginalia/annotations, not terminal UI. This carries the "builder" signal.
- **Serif reading content** (headlines, What/Why/Your-work text) — reads as journal prose. This carries the "reading feel."

Both sit on a warm paper aesthetic (grid/ruled-line texture, soft rounded corners, subtle paper-lift shadows) rather than a dark terminal dashboard or a glossy SaaS look. The goal: this reads as a genuine personal tool built with care, not a template — and it doubles as portfolio material for "AI builder" job applications, so the craft has to be visible to a stranger landing on it cold.

This direction was iterated in conversation (see decision log below) and validated with a Figma Make mockup generated from a detailed prompt — the mockup confirmed the direction works and surfaced three worthwhile additions (issue number, dot legend, footer transparency line) now folded into this spec. Save that mockup image into the repo (e.g. `/design/reference-homepage.png`) as the visual anchor for build.

---

## Color Palette

All pairings verified against the background using the WCAG relative-luminance contrast formula — not just picked to look right. There's no official "WCAG-approved palette"; contrast is math between a specific foreground/background pair, so these ratios were calculated for these exact values.

| Token | Value | Contrast vs. background | WCAG | Use |
|---|---|---|---|---|
| Background | `#F7F6F2` | — | — | warm paper, not stark white |
| Surface (cards) | `#FFFFFF` / `#FCFBF8` | ≥ background ratio | — | elevated cards/panels |
| Border | `#DEDCD3` | — (decorative) | — | hairline dividers |
| Text primary | `#1A1B1E` | 15.9:1 | AAA | headlines, body copy |
| Text muted | `#63666B` | 4.7:1 | AA | metadata, timestamps, source tags |
| Accent (single) | `#C1440E` deep rust | 4.74:1 | AA | links, active states, margin rule, "try this" dot, citation chips, hover borders |
| Warning text | `#8A5A00` deep ochre | 5.49:1 | AA | stale-digest banner text (on a pale yellow `#FDF3DC` fill) |

**One accent color does all the signaling work** — deliberately, instead of a color-per-beat scheme (which is what makes most digest sites look corporate/generic). Every time rust appears, it means the same thing: this matters, this is active, this is actionable.

**Note on the earlier bright orange (`#FF6A3D`):** an initial pass proposed a brighter, more saturated orange for a dark-background version of this design. When the background moved to light/paper, that color failed WCAG contrast outright (~2.6:1, under even the 3:1 minimum for non-text graphical elements like the dot indicator) — a good example of a color that looks "strong" but doesn't survive the math on a light surface. The deep rust above is the corrected, verified replacement, and is the only accent this design uses now.

---

## Typography

- **JetBrains Mono** — all UI chrome: nav, dates, source tags, citation chips, tab labels, the issue number, the archive rail. Deliberately recast as "typewriter/field-notes" rather than "terminal," which is why it pairs with a serif rather than another mono/sans for body text.
- **Source Serif 4** — headlines and all reading content (What/Why/Your-work lines). Reading dense summary text in monospace hurts skimmability; serif adds editorial warmth against the technical chrome.
- This pairing is the single biggest driver of the dual identity (builder + journal) and is load-bearing — don't substitute a generic sans-only system, it would collapse the whole concept into a generic content site.
- Sizing: headline ~20-21px serif bold; body ~16px/1.65 line-height serif; mono labels ~12-13px uppercase, wide letter-spacing.

---

## Depth & Texture

- **Corners:** soft rounding, ~8px on cards/panels — reads as a paper page corner, not an app bubble.
- **Depth:** a subtle, warm-toned drop shadow suggesting a page lifted slightly off the surface beneath it, plus hairline borders as a secondary depth cue. This is a deliberate reversal of an earlier "borders only, zero shadow" rule explored during the Technical-Mono-only phase of this project — that rule made sense for a pure dev-tool aesthetic; it doesn't for a notebook page, which genuinely casts a soft shadow.
- **Texture:** subtle paper-grain (SVG noise filter) across the background, plus faint grid/ruled lines behind the reading content area — closer to graph/lab-notebook paper than plain ruled paper, which fits the "AI builder / researcher" identity better.
- Restraint matters here: no dog-ears, no stitched-binding illustration, no literal skeuomorphism. The notebook feeling comes from structure (corners, texture, margin rule), not decoration — that's what keeps it credible as a portfolio piece instead of twee.

---

## Layout

```
┌────────────────────────────────────────────────┐
│  > ai24                            2026-08-20    │
│  daily curated AI / Design / Voice AI briefing   │  Issue #214
├────────────────┬─────────────────────────────────┤
│  PREVIOUS 7 DAYS│  [ AI ] [ DESIGN ] [ VOICE ] · 3 items │
│  2026-08-20  ●  │                                  │
│  2026-08-19     │   -- item cards --              │
│  ...            │                                  │
│  2026-08-14     │                                  │
│  View full       │                                  │
│  archive →       │                                  │
│  [ activity      │                                  │
│    sparkline ]   │                                  │
│  ● try this      │                                  │
│  ○ read this     │                                  │
└────────────────┴─────────────────────────────────┘
Curated and synthesized daily by an automated pipeline.
Reviewed by a human on good days. — hello@ai24.fyi · GitHub
```

- **Header** (full width): mono wordmark `> ai24`, tagline beneath, date + a running **issue number** (e.g. "Issue #214" — a day-count, cheap to compute, reinforces the "ongoing publication" feel) top-right. Thin rust underline.
- **Left sidebar:** "PREVIOUS 7 DAYS" label, notebook-tab-styled date list (protruding tab shape, not a flat list), active date highlighted with a rust border. "View full archive →" link below for anything older than 7 days. Digest activity sparkline beneath that (item volume over recent days) — **only renders once the archive has ≥2 days of history**; no special empty state needed for day one, it simply doesn't show yet. A **dot legend** (● try this / ○ read this) sits at the bottom of the sidebar, so a first-time visitor can decode the indicator without guessing.
- **Main content:** beat tabs (AI / DESIGN / VOICE) styled as notebook index-tab dividers, with the **item count shown inline on the same row as the tabs** (e.g. "· 3 items") rather than as a separate repeated line below.
- **Item card:** rust vertical rule down the left edge (echoing a notebook's red margin line); publisher-name citation chip top-left (e.g. "OpenAI ↗", styled like a typewritten stamp, links to source); try-this/read-this dot top-right; serif bold headline; three serif lines (What / Why / Your work) with bold inline lead-in labels, tightly spaced.
- **Footer:** the transparency line — *"Curated and synthesized daily by an automated pipeline. Reviewed by a human on good days."* — plus contact and a GitHub repo link. This is the portfolio-context anchor: a visitor who lands here with zero context needs to understand what they're looking at without you there to explain it.
- **Individual day pages:** prev/next-day navigation, not just a bounce back to the archive list.
- **Mobile:** the sidebar collapses into a slide-out drawer (matches how ChatGPT/Perplexity handle the same history-rail problem on small screens); main content stays full-width. This matters because the primary real-world entry point is the 9 AM push notification → tap on phone, not desktop browsing.

---

## Data Visualization Scope

- **In scope:** archive activity sparkline in the sidebar (item volume/source trends over time — becomes more interesting the longer the archive runs, since it's a byproduct of the pipeline's own data); opportunistic source thumbnails (`og:image` pulled from blog sources where available; arXiv items stay text-only, graceful degradation, not load-bearing).
- **Explicitly out of scope:** a per-item "why this ranked" mini radar/bar visualization (source authority/relevance/novelty scores) was considered and intentionally cut to keep item cards clean and the ranking prompt simpler.

---

## Accessibility

- WCAG AA minimum for every text pairing in use (see color table above for verified ratios).
- Every interactive element (tabs, archive links, citation chips) needs hover, focus-visible, and active states — no exceptions.
- `prefers-reduced-motion` respected — all transitions degrade to instant/none.
- Keyboard-navigable tabs and archive list.

---

## Micro-interactions

Motion as signage, not decoration — every animation should confirm a state change, nothing purely ornamental.

- Tab switch: 150-200ms fade/slide, spring easing, `transform`/`opacity` only.
- Card hover: border shifts to the rust accent, slight `translateY(-2px)` — no shadow bloom.
- Citation chip hover: small popover (source name), click opens in a new tab.
- "Try this" dot: a very subtle pulse — draws the eye toward actionable items specifically, directly reflecting the personalization blurb's stated priority. No pulse on "read this" items.

---

## Content Budget (drives card sizing)

See PRD.md's Summarization section for the authoritative numbers (headline ≤70 chars; What/Why/Your-work soft target ~100-150 chars each, hard ceiling ~220-250 chars). Card layout should be tested against both the soft-target length and the hard-ceiling length to confirm it never breaks — a Figma Make mockup pass generated placeholder copy well over these limits, which was a useful stress test showing what happens if the budget isn't enforced (noticeably less skimmable, lines wrap to two lines each). Enforce in code, not just in the prompt.

---

## Decision Log (for context on *why*, not just *what*)

- Chose **Astro over Next.js**: no client-side interactivity needed for a templated content site.
- Chose **tabbed-by-beat over one continuous scroll**: trades a small amount against the strict "skim in one pass" reading of the 2-minute goal, in exchange for more interaction-design craft to demonstrate — a deliberate call given this is portfolio material.
- Chose **publisher-name citation chips over numbered footnotes**: matches the single-source-per-item model (no multi-source merging), and is more scannable while skimming than a number requiring a hover to decode.
- Chose **full notebook pivot over a layered/subtle version**: committing fully to one coherent identity rather than hedging between two.
- Considered and rejected a **per-item ranking-score visualization** and **multi-source citation merging** — both would have added real pipeline complexity (same-story detection across sources, expanded LLM output schema) for a smaller payoff than the archive dashboard and thumbnails already provide.
