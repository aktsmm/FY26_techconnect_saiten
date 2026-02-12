"""End-to-end test script for saiten-mcp tools."""

import asyncio
import json


async def test_list_submissions():
    """Test list_submissions tool."""
    from saiten_mcp.tools.submissions import list_submissions

    print("=" * 60)
    print("TEST: list_submissions")
    print("=" * 60)

    results = await list_submissions(state="all")
    print(f"Total submissions: {len(results)}")

    for r in results[:5]:
        num = r["issue_number"]
        track = r["track"]
        name = r["project_name"][:50]
        print(f"  #{num} [{track}] {name}")

    if len(results) > 5:
        print(f"  ... and {len(results) - 5} more")

    # Track distribution
    tracks = {}
    for r in results:
        t = r["track"]
        tracks[t] = tracks.get(t, 0) + 1
    print(f"\nTrack distribution: {tracks}")

    return results


async def test_get_submission_detail(issue_number: int):
    """Test get_submission_detail tool."""
    from saiten_mcp.tools.submissions import get_submission_detail

    print("\n" + "=" * 60)
    print(f"TEST: get_submission_detail(#{issue_number})")
    print("=" * 60)

    detail = await get_submission_detail(issue_number)
    print(f"  Title: {detail['title']}")
    print(f"  Track: {detail['track']}")
    print(f"  Project: {detail['project_name']}")
    print(f"  Repo URL: {detail['repo_url']}")
    print(f"  Has Demo: {detail['has_demo']}")
    print(f"  Technologies: {detail['technologies']}")
    readme = detail.get("readme_content")
    if readme:
        print(f"  README: {len(readme)} chars (first 100: {readme[:100]}...)")
    else:
        print("  README: None")

    return detail


async def test_get_scoring_rubric():
    """Test get_scoring_rubric tool."""
    from saiten_mcp.tools.rubrics import get_scoring_rubric

    print("\n" + "=" * 60)
    print("TEST: get_scoring_rubric")
    print("=" * 60)

    for track in ["creative-apps", "reasoning-agents", "enterprise-agents"]:
        rubric = await get_scoring_rubric(track)
        criteria_names = [c["name"] for c in rubric["criteria"]]
        print(f"  {track}: {len(rubric['criteria'])} criteria, "
              f"weight={rubric['total_weight']}")
        print(f"    -> {criteria_names}")


async def test_save_scores():
    """Test save_scores tool."""
    from saiten_mcp.tools.scores import save_scores

    print("\n" + "=" * 60)
    print("TEST: save_scores (mock data)")
    print("=" * 60)

    mock_scores = [
        {
            "issue_number": 9999,
            "project_name": "Test Project",
            "track": "creative-apps",
            "criteria_scores": {
                "Accuracy & Relevance": 7,
                "Reasoning & Multi-step Thinking": 6,
                "Creativity & Originality": 8,
                "UX & Presentation": 7,
                "Reliability & Safety": 6,
            },
            "weighted_total": 67.8,
            "strengths": ["Good test coverage", "Clean code"],
            "improvements": ["Needs better docs"],
            "summary": "A solid test project.",
        }
    ]

    result = await save_scores(mock_scores)
    print(f"  Saved: {result['saved_count']} new, "
          f"{result['updated_count']} updated, "
          f"{result['total_in_store']} total")
    print(f"  File: {result['file_path']}")

    # Test idempotency - save again
    result2 = await save_scores(mock_scores)
    print(f"  Re-save: {result2['saved_count']} new, "
          f"{result2['updated_count']} updated (should be 1)")

    return result


async def test_generate_ranking_report():
    """Test generate_ranking_report tool."""
    from saiten_mcp.tools.reports import generate_ranking_report

    print("\n" + "=" * 60)
    print("TEST: generate_ranking_report")
    print("=" * 60)

    result = await generate_ranking_report(top_n=5)
    print(f"  Report: {result['report_path']}")
    print(f"  Total scored: {result['total_scored']}")
    print(f"  Top entries: {result['top_entries']}")

    return result


async def main():
    print("Saiten MCP — End-to-End Test\n")

    # 1. list_submissions
    submissions = await test_list_submissions()

    # 2. get_submission_detail (pick first submission)
    if submissions:
        first = submissions[0]["issue_number"]
        await test_get_submission_detail(first)

    # 3. get_scoring_rubric
    await test_get_scoring_rubric()

    # 4. save_scores
    await test_save_scores()

    # 5. generate_ranking_report
    await test_generate_ranking_report()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
