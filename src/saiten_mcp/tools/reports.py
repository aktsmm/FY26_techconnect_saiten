"""Saiten MCP — Reports tool.

Generates Markdown ranking reports from data/scores.json
and outputs them to the reports/ directory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from saiten_mcp.server import mcp, DATA_DIR, REPORTS_DIR

logger = logging.getLogger(__name__)

SCORES_FILE = DATA_DIR / "scores.json"

TRACK_EMOJI: dict[str, str] = {
    "creative-apps": "🎨",
    "reasoning-agents": "🧠",
    "enterprise-agents": "💼",
}

TRACK_DISPLAY: dict[str, str] = {
    "creative-apps": "Creative Apps",
    "reasoning-agents": "Reasoning Agents",
    "enterprise-agents": "Enterprise Agents",
}


def _load_scores() -> dict[str, Any]:
    """Load scores.json. Returns an empty store if file is missing or empty."""
    if not SCORES_FILE.exists():
        logger.warning("scores.json not found: %s", SCORES_FILE)
        return {"metadata": {}, "scores": []}

    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load scores.json: %s", exc)
        return {"metadata": {}, "scores": []}

    if not isinstance(data, dict):
        logger.warning("scores.json has invalid format")
        return {"metadata": {}, "scores": []}

    return data


def _fmt_score(score: float | int) -> str:
    """Format a score to 1 decimal place."""
    return f"{float(score):.1f}"


def _build_ranking_md(
    scores: list[dict[str, Any]],
    metadata: dict[str, Any],
    top_n: int,
) -> str:
    """Build a Markdown ranking report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    scored_count = metadata.get("scored_count", len(scores))
    total_submissions = metadata.get("total_submissions", len(scores))

    lines: list[str] = []

    # --- Header ---
    lines.append("# 🏆 Agents League @ TechConnect — Scoring Ranking")
    lines.append("")
    lines.append(f"> Auto-generated: {timestamp}")
    lines.append(f"> Scored: {scored_count} / {total_submissions} submissions")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Top N ---
    top_entries = scores[:top_n]
    lines.append(f"## 🥇 Top {top_n}")
    lines.append("")
    lines.append("| Rank | Project | Track | Submitter | Score |")
    lines.append("|------|---------|-------|-----------|-------|")
    for rank, entry in enumerate(top_entries, start=1):
        name = entry.get("project_name", "N/A")
        track = entry.get("track", "")
        emoji = TRACK_EMOJI.get(track, "")
        score = _fmt_score(entry.get("weighted_total", 0))
        gh_user = entry.get("github_username") or ""
        issue_num = entry.get("issue_number", "")
        issue_url = entry.get("issue_url") or ""
        # Link project name to Issue
        name_linked = f"[{name}]({issue_url})" if issue_url else name
        # Link GitHub username
        user_linked = f"[@{gh_user}](https://github.com/{gh_user})" if gh_user else "—"
        lines.append(f"| {rank} | {name_linked} | {emoji} | {user_linked} | {score} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Track Top 3 ---
    lines.append("## 🏅 Track Top 3")
    lines.append("")

    for track_key in ["creative-apps", "reasoning-agents", "enterprise-agents"]:
        emoji = TRACK_EMOJI.get(track_key, "")
        display = TRACK_DISPLAY.get(track_key, track_key)
        lines.append(f"### {emoji} {display}")
        lines.append("")
        lines.append("| Rank | Project | Submitter | Score |")
        lines.append("|------|---------|-----------|-------|")

        track_scores = [s for s in scores if s.get("track") == track_key]
        for rank, entry in enumerate(track_scores[:3], start=1):
            name = entry.get("project_name", "N/A")
            score = _fmt_score(entry.get("weighted_total", 0))
            issue_url = entry.get("issue_url") or ""
            gh_user = entry.get("github_username") or ""
            name_linked = f"[{name}]({issue_url})" if issue_url else name
            user_linked = f"[@{gh_user}](https://github.com/{gh_user})" if gh_user else "—"
            lines.append(f"| {rank} | {name_linked} | {user_linked} | {score} |")

        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Full Score List ---
    lines.append("## 📊 All Submissions")
    lines.append("")
    lines.append("| # | Issue | Project | Track | Submitter | Score | Scored At |")
    lines.append("|---|-------|---------|-------|-----------|-------|-----------|")

    for idx, entry in enumerate(scores, start=1):
        issue = entry.get("issue_number", "")
        name = entry.get("project_name", "N/A")
        track = entry.get("track", "")
        emoji = TRACK_EMOJI.get(track, "")
        score = _fmt_score(entry.get("weighted_total", 0))
        issue_url = entry.get("issue_url") or ""
        gh_user = entry.get("github_username") or ""
        name_linked = f"[{name}]({issue_url})" if issue_url else name
        user_linked = f"[@{gh_user}](https://github.com/{gh_user})" if gh_user else "—"
        scored_at = entry.get("scored_at", "")
        if scored_at:
            try:
                dt = datetime.fromisoformat(scored_at)
                scored_at = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass
        lines.append(f"| {idx} | [#{issue}]({issue_url}) | {name_linked} | {emoji} | {user_linked} | {score} | {scored_at} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Individual Evaluation Summaries ---
    lines.append("## 📋 Individual Evaluation Summaries")
    lines.append("")

    for entry in scores:
        issue = entry.get("issue_number", "")
        name = entry.get("project_name", "N/A")
        track = entry.get("track", "")
        emoji = TRACK_EMOJI.get(track, "")
        display = TRACK_DISPLAY.get(track, track)
        score = _fmt_score(entry.get("weighted_total", 0))

        strengths_list: list[str] = entry.get("strengths", [])
        improvements_list: list[str] = entry.get("improvements", [])
        summary = entry.get("summary", "")

        strengths = ", ".join(strengths_list) if strengths_list else "—"
        improvements = ", ".join(improvements_list) if improvements_list else "—"

        lines.append(f"### #{issue}: {name}")
        lines.append(f"- **Track**: {emoji} {display}")
        lines.append(f"- **Score**: {score}/100")
        lines.append(f"- **Strengths**: {strengths}")
        lines.append(f"- **Improvements**: {improvements}")
        lines.append(f"- **Summary**: {summary}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def generate_ranking_report(
    top_n: int = 10,
) -> dict[str, Any]:
    """Generate a Markdown ranking report and save to reports/ranking.md.

    Reads scoring results from data/scores.json and produces a report
    containing overall ranking, per-track ranking, and individual
    evaluation summaries.

    Args:
        top_n: Number of top entries to highlight (default: 10).

    Returns:
        Result dict (report_path, total_scored, top_n, top_entries).
    """
    store = _load_scores()
    scores: list[dict[str, Any]] = store.get("scores", [])
    metadata: dict[str, Any] = store.get("metadata", {})

    if not scores:
        logger.info("No scoring data found. Generating empty report.")

    # Sort by weighted_total descending (insurance: already sorted on save)
    scores.sort(key=lambda x: x.get("weighted_total", 0), reverse=True)

    # Generate Markdown
    md_content = _build_ranking_md(scores, metadata, top_n)

    # Write to file
    report_path = REPORTS_DIR / "ranking.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info("Ranking report generated: %s", report_path)

    # Build top N summary for return value
    top_entries: list[dict[str, Any]] = []
    for rank, entry in enumerate(scores[:top_n], start=1):
        top_entries.append(
            {
                "rank": rank,
                "project_name": entry.get("project_name", "N/A"),
                "track": entry.get("track", ""),
                "score": entry.get("weighted_total", 0),
            }
        )

    return {
        "report_path": str(report_path),
        "total_scored": len(scores),
        "top_n": top_n,
        "top_entries": top_entries,
    }
