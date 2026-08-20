"""Write the day's digest to /data/digests/, commit, and push.

Reads pipeline/.staging/ranked.json (from rank_summarize.py). With --dry-run,
writes to a scratch path instead and skips git entirely — always test with
this flag before ever touching the real committed archive.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

RANKED_PATH = Path(__file__).parent / ".staging" / "ranked.json"
ARCHIVE_DIR = Path(__file__).parent.parent / "data" / "digests"
DRY_RUN_DIR = Path(__file__).parent / ".staging" / "dry-run-digests"


def load_ranked():
    if not RANKED_PATH.exists():
        raise FileNotFoundError(f"{RANKED_PATH} not found — run rank_summarize.py first")
    return json.loads(RANKED_PATH.read_text())


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_commit_and_push(filepath, date_str):
    code, _, err = run(["git", "add", str(filepath)])
    if code != 0:
        print(f"  ✗ git add failed: {err}", file=sys.stderr)
        return False

    code, out, err = run(["git", "commit", "-m", f"Digest for {date_str}"])
    if code != 0:
        if "nothing to commit" in (out + err):
            print("  · nothing to commit (identical content already committed)")
            return True
        print(f"  ✗ git commit failed: {err}", file=sys.stderr)
        return False
    print(f"  ✓ committed: {out.splitlines()[0] if out else ''}")

    code, out, _ = run(["git", "remote"])
    if code != 0 or not out.strip():
        print("  · no git remote configured — skipping push (local commit only)")
        return True

    code, _, err = run(["git", "push"])
    if code != 0:
        print(f"  ✗ git push failed: {err}", file=sys.stderr)
        return False
    print("  ✓ pushed")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write to a scratch path and skip git entirely — never touches the real archive",
    )
    args = parser.parse_args()

    digest = load_ranked()
    date_str = digest["date"]

    if args.dry_run:
        DRY_RUN_DIR.mkdir(parents=True, exist_ok=True)
        filepath = DRY_RUN_DIR / f"{date_str}.json"
        filepath.write_text(json.dumps(digest, indent=2))
        print(f"[DRY RUN] Wrote {filepath} — did not touch the real archive or git")
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = ARCHIVE_DIR / f"{date_str}.json"

    if filepath.exists():
        print(f"  ! {filepath} already exists — overwriting with today's latest run")

    filepath.write_text(json.dumps(digest, indent=2))
    print(f"Wrote {filepath}")

    if not git_commit_and_push(filepath, date_str):
        sys.exit(1)


if __name__ == "__main__":
    main()
