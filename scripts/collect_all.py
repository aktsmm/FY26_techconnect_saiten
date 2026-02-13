import asyncio
import json
import sys
import time

sys.path.insert(0, "src")
from saiten_mcp.tools.submissions import get_submission_detail
from saiten_mcp.server import rate_limiter

VALID_ISSUES = [53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10]

async def main():
    rate_limiter.max_calls = 100  # increase limit for batch collection
    all_details = []
    errors = []
    for i, issue_num in enumerate(VALID_ISSUES):
        try:
            detail = await get_submission_detail(issue_num)
            pname = detail.get("project_name", "?")
            track = detail.get("track", "?")
            has_readme = "yes" if detail.get("readme_content") else "no"
            print(f"OK: #{issue_num} ({pname} / {track}) readme={has_readme}", flush=True)
            all_details.append(detail)
        except Exception as e:
            errors.append({"issue_number": issue_num, "error": str(e)})
            print(f"ERR: #{issue_num}: {e}", flush=True)

    with open("data/collected_submissions.json", "w", encoding="utf-8") as f:
        json.dump({"submissions": all_details, "errors": errors}, f, ensure_ascii=False, indent=2)

    # Summary by track
    tracks = {}
    for d in all_details:
        t = d.get("track", "unknown")
        tracks[t] = tracks.get(t, 0) + 1
    print(f"\nTotal collected: {len(all_details)}, Errors: {len(errors)}")
    print(f"Track distribution: {tracks}")

asyncio.run(main())
