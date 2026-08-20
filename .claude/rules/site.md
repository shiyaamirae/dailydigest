---
paths:
  - "site/**"
---

# Site (Astro) Rules

## Design Source of Truth

`design.md` and `reference ui.png` (the Figma Make mockup) are the visual spec — match them, don't
improvise. If something isn't covered by either (a component state, an edge case), ask rather than
guessing at a plausible-looking default.

## Build Constraints

- **The Astro site needs zero secrets at build time** — it only reads already-committed JSON from
  `/data/digests/`. Keep it that way; don't introduce a build-time API call to the site without a
  real reason to revisit this.
- No client-side framework/hydration needed — this is a static, content-driven site. Reach for
  Astro's default static output before reaching for an island or client directive.

## Testing Locally

Run the Astro dev server (`npm run dev` inside `/site`) against a locally-generated digest JSON
(from the pipeline's local test run) to confirm it renders per `design.md` before pushing.

## Adding Packages

```bash
npm install {package}          # inside /site
```
