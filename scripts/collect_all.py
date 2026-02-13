"""Incremental submission collector.

Always fetches the latest Issue list from GitHub via list_submissions(),
compares with existing data/collected_submissions.json, and fetches
details only for new or updated submissions.  Existing entries are
preserved and merged with fresh data so no work is lost.

Usage:
    python scripts/collect_all.py            # incremental (default)
    python scripts/collect_all.py --force     # re-collect everything
"""

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, "src")
from saiten_mcp.tools.submissions import get_submission_detail, list_submissions
from saiten_mcp.server import rate_limiter

DATA_FILE = pathlib.Path("data/collected_submissions.json")


def _load_existing() -> dict:
    """Load existing collected data. Returns empty structure if missing."""
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"submissions": [], "errors": []}


def _index_by_issue(submissions: list[dict]) -> dict[int, dict]:
    """Build {issue_number: submission_detail} lookup."""
    return {s["issue_number"]: s for s in submissions if "issue_number" in s}


async def main() -> None:
    force = "--force" in sys.argv
    rate_limiter.max_calls = 150  # increase limit for batch collection

    # --- Step 1: Discover current Issues from GitHub -----------------------
    print("=== Fetching latest submission list from GitHub ===", flush=True)
    live_issues = await list_submissions(state="all")
    live_numbers = sorted(
        [i["issue_number"] for i in live_issues], reverse=True
    )
    print(f"Found {len(live_numbers)} submissions on GitHub", flush=True)

    # --- Step 2: Load existing data & detect new Issues --------------------
    existing = _load_existing()
    existing_index = _index_by_issue(existing.get("submissions", []))
    existing_numbers = set(existing_index.keys())

    if force:
        to_fetch = set(live_numbers)
        print(f"--force: re-collecting all {len(to_fetch)} submissions", flush=True)
    else:
        to_fetch = set(live_numbers) - existing_numbers
        if to_fetch:
            print(
                f"New submissions detected: {sorted(to_fetch, reverse=True)}",
                flush=True,
            )
        else:
            print("No new submissions. Existing data is up to date.", flush=True)

    # --- Step 3: Fetch details for new Issues ------------------------------
    fresh_details: list[dict] = []
    errors: list[dict] = []

    for issue_num in sorted(to_fetch, reverse=True):
        try:
            detail = await get_submission_detail(issue_num)
            pname = detail.get("project_name", "?")
            track = detail.get("track", "?")
            has_readme = "yes" if detail.get("readme_content") else "no"
            print(
                f"  OK: #{issue_num} ({pname} / {track}) readme={has_readme}",
                flush=True,
            )
            fresh_details.append(detail)
        except Exception as e:
            errors.append({"issue_number": issue_num, "error": str(e)})
            print(f"  ERR: #{issue_num}: {e}", flush=True)

    # --- Step 4: Merge — fresh overwrites existing duplicates --------------
    merged_index = dict(existing_index)  # start with existing
    for detail in fresh_details:
        merged_index[detail["issue_number"]] = detail  # upsert

    # Remove issues that no longer appear on GitHub (deleted/transferred)
    live_set = set(live_numbers)
    removed = set(merged_index.keys()) - live_set
    for r in removed:
        del merged_index[r]
    if removed:
        print(f"Removed {len(removed)} issues no longer on GitHub: {sorted(removed)}", flush=True)

    # Sort by issue number descending
    merged_submissions = sorted(
        merged_index.values(), key=lambda s: s["issue_number"], reverse=True
    )

    # Merge errors (keep old errors for issues not re-fetched)
    old_errors = {
        e["issue_number"]: e
        for e in existing.get("errors", [])
        if e["issue_number"] not in to_fetch
    }
    for e in errors:
        old_errors[e["issue_number"]] = e
    merged_errors = sorted(old_errors.values(), key=lambda e: e["issue_number"], reverse=True)

    # --- Step 5: Save ------------------------------------------------------
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"submissions": merged_submissions, "errors": merged_errors},
            f,
            ensure_ascii=False,
            indent=2,
        )

    # --- Step 6: Summary ---------------------------------------------------
    tracks: dict[str, int] = {}
    for d in merged_submissions:
        t = d.get("track", "unknown")
        tracks[t] = tracks.get(t, 0) + 1

    print(f"\n{'=' * 50}", flush=True)
    print(f"Total submissions: {len(merged_submissions)}", flush=True)
    print(f"  Newly fetched:   {len(fresh_details)}", flush=True)
    print(f"  Carried over:    {len(merged_submissions) - len(fresh_details)}", flush=True)
    print(f"  Errors:          {len(merged_errors)}", flush=True)
    print(f"Track distribution: {tracks}", flush=True)
    print(f"Data saved to: {DATA_FILE}", flush=True)


asyncio.run(main())
