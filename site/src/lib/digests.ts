import fs from "node:fs";
import path from "node:path";

export type Beat = "AI" | "Design" | "Voice AI";

export type Item = {
  title: string;
  source: string;
  url: string;
  what: string;
  why: string;
  impact: string;
  practical: boolean;
};

export type Digest = {
  date: string; // YYYY-MM-DD
  beats: Record<Beat, Item[]>;
};

export const BEATS: Beat[] = ["AI", "Design", "Voice AI"];

// Anchored to process.cwd() rather than import.meta.url: Astro/Vite bundles
// this module into dist/.prerender/chunks/ at build time, which would break
// an import.meta.url-relative path. The dev server and build are always run
// from inside /site (see .claude/rules/site.md), so cwd -> ../data/digests
// is stable across dev, build, and CI.
const ARCHIVE_DIR = path.resolve(process.cwd(), "../data/digests");

function readDigest(filepath: string): Digest {
  const raw = fs.readFileSync(filepath, "utf-8");
  return JSON.parse(raw) as Digest;
}

/** All digests, sorted newest-first. Empty array if the archive doesn't exist yet. */
export function loadAllDigests(): Digest[] {
  if (!fs.existsSync(ARCHIVE_DIR)) return [];
  return fs
    .readdirSync(ARCHIVE_DIR)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .reverse()
    .map((f) => readDigest(path.join(ARCHIVE_DIR, f)));
}

export function loadDigest(date: string): Digest | null {
  const filepath = path.join(ARCHIVE_DIR, `${date}.json`);
  if (!fs.existsSync(filepath)) return null;
  return readDigest(filepath);
}

export function loadLatestDigest(): Digest | null {
  const all = loadAllDigests();
  return all[0] ?? null;
}

export function itemCount(digest: Digest): number {
  return BEATS.reduce((sum, beat) => sum + (digest.beats[beat]?.length ?? 0), 0);
}

/** Day-count since the archive's first entry — used for the "Issue #N" header. */
export function issueNumber(date: string, all: Digest[]): number {
  const sorted = [...all].sort((a, b) => a.date.localeCompare(b.date));
  const idx = sorted.findIndex((d) => d.date === date);
  return idx >= 0 ? idx + 1 : sorted.length + 1;
}

/** Today's date in IST (UTC+5:30) — same timezone convention the pipeline publishes in. */
export function todayIST(): string {
  const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;
  const now = new Date(Date.now() + IST_OFFSET_MS);
  return now.toISOString().slice(0, 10);
}
