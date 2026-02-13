"""Saiten — Full scoring pipeline.

Fetches all 42 submissions, evaluates each against track-specific rubrics,
saves scores, and generates the ranking report.

Scoring heuristics are based on objective signals from the submission data:
  - Checklist completion status
  - README presence and length
  - Demo availability
  - Technologies count and depth
  - Technical highlights quality
  - Repository URL presence
  - Setup instructions
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring helpers — data-driven heuristic evaluation
# ---------------------------------------------------------------------------

# Keywords that indicate advanced reasoning / agentic patterns
REASONING_KEYWORDS = [
    "chain-of-thought", "cot", "react", "reflection", "self-correct",
    "multi-agent", "orchestrat", "planner", "pipeline", "workflow",
    "semantic kernel", "autogen", "langchain", "langgraph",
    "tool use", "function call", "rag", "grounding",
    "evaluation", "feedback loop", "retry", "iterative",
]

# Keywords that indicate reliability / safety
RELIABILITY_KEYWORDS = [
    "error handl", "try", "catch", "except", "retry", "rate limit",
    "authentication", "oauth", "security", "helmet", "cors",
    "validation", "sanitiz", "encrypt", ".env", "secret",
    "test", "pytest", "jest", "unit test", "logging", "monitor",
]

# Keywords that indicate MCP / Copilot usage
COPILOT_MCP_KEYWORDS = [
    "mcp", "model context protocol", "copilot", "github copilot",
    "copilot agent", "agent.md", "mcp server", "fastmcp",
    "copilot chat", "copilot extension", "copilot sdk",
]

# Keywords for enterprise / M365
ENTERPRISE_KEYWORDS = [
    "adaptive card", "connected agent", "declarative agent",
    "teams", "m365", "microsoft 365", "copilot studio",
    "sharepoint", "graph api", "entra", "oauth",
    "agents toolkit", "custom engine", "bot framework",
]

# Keywords for creativity / innovation
CREATIVITY_KEYWORDS = [
    "novel", "innovat", "unique", "creative", "original",
    "first", "new approach", "reimagin", "transform",
    "ai-powered", "intelligent", "smart", "automat",
    "real-time", "live", "interactive", "dynamic",
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def _score_from_signals(
    hits: int, max_keywords: int, base: int = 4, ceiling: int = 9
) -> int:
    """Convert keyword hit count to a 1-10 score."""
    if max_keywords == 0:
        return base
    ratio = min(hits / max_keywords, 1.0)
    return min(ceiling, max(1, base + round(ratio * (ceiling - base))))


def _evaluate_creative_apps(detail: dict[str, Any]) -> dict[str, Any]:
    """Score a Creative Apps submission."""
    readme = detail.get("readme_content") or ""
    desc = detail.get("description") or ""
    highlights = detail.get("technical_highlights") or ""
    setup = detail.get("setup_summary") or ""
    demo_desc = detail.get("demo_description") or ""
    techs = detail.get("technologies") or []
    checklist = detail.get("submission_checklist") or {}
    has_demo = detail.get("has_demo", False)
    has_repo = detail.get("repo_url") is not None

    corpus = f"{readme} {desc} {highlights} {setup} {demo_desc}".lower()
    tech_str = " ".join(techs).lower()
    full_text = f"{corpus} {tech_str}"

    # --- Accuracy & Relevance (Copilot + MCP usage) ---
    copilot_hits = _count_keyword_hits(full_text, COPILOT_MCP_KEYWORDS)
    checklist_done = sum(1 for v in checklist.values() if v)
    checklist_total = max(len(checklist), 1)
    checklist_ratio = checklist_done / checklist_total

    acc_base = 4 if has_repo else 2
    acc_base += round(checklist_ratio * 2)
    acc_score = min(10, acc_base + min(copilot_hits, 3))

    # --- Reasoning & Multi-step Thinking ---
    reasoning_hits = _count_keyword_hits(full_text, REASONING_KEYWORDS)
    rea_score = _score_from_signals(reasoning_hits, 5, base=3, ceiling=9)

    # --- Creativity & Originality ---
    creativity_hits = _count_keyword_hits(full_text, CREATIVITY_KEYWORDS)
    tech_diversity = min(len(techs), 10)
    cre_base = 3 + min(tech_diversity // 3, 3)
    cre_score = min(10, cre_base + min(creativity_hits, 3))

    # --- UX & Presentation ---
    ux_score = 3
    if has_repo:
        ux_score += 1
    if has_demo:
        ux_score += 2
    if len(readme) > 2000:
        ux_score += 1
    if len(readme) > 5000:
        ux_score += 1
    if setup and setup.lower() not in ("_no response_", ""):
        ux_score += 1
    ux_score = min(10, ux_score)

    # --- Reliability & Safety ---
    rel_hits = _count_keyword_hits(full_text, RELIABILITY_KEYWORDS)
    rel_score = _score_from_signals(rel_hits, 5, base=3, ceiling=9)

    criteria_scores = {
        "Accuracy & Relevance": acc_score,
        "Reasoning & Multi-step Thinking": rea_score,
        "Creativity & Originality": cre_score,
        "UX & Presentation": ux_score,
        "Reliability & Safety": rel_score,
    }

    weights = {
        "Accuracy & Relevance": 0.222,
        "Reasoning & Multi-step Thinking": 0.222,
        "Creativity & Originality": 0.167,
        "UX & Presentation": 0.167,
        "Reliability & Safety": 0.222,
    }

    weighted_total = sum(
        criteria_scores[k] * weights[k] for k in criteria_scores
    ) * 10

    return _build_score_entry(detail, criteria_scores, weighted_total, full_text)


def _evaluate_reasoning_agents(detail: dict[str, Any]) -> dict[str, Any]:
    """Score a Reasoning Agents submission."""
    readme = detail.get("readme_content") or ""
    desc = detail.get("description") or ""
    highlights = detail.get("technical_highlights") or ""
    setup = detail.get("setup_summary") or ""
    demo_desc = detail.get("demo_description") or ""
    techs = detail.get("technologies") or []
    checklist = detail.get("submission_checklist") or {}
    has_demo = detail.get("has_demo", False)
    has_repo = detail.get("repo_url") is not None

    corpus = f"{readme} {desc} {highlights} {setup} {demo_desc}".lower()
    tech_str = " ".join(techs).lower()
    full_text = f"{corpus} {tech_str}"

    # --- Accuracy & Relevance (Foundry / scenario fit) ---
    foundry_kw = ["foundry", "azure ai", "azure openai", "gpt", "ai project",
                  "social media", "communication", "content"]
    foundry_hits = _count_keyword_hits(full_text, foundry_kw)
    checklist_done = sum(1 for v in checklist.values() if v)
    checklist_total = max(len(checklist), 1)
    acc_base = 4 if has_repo else 2
    acc_base += round((checklist_done / checklist_total) * 2)
    acc_score = min(10, acc_base + min(foundry_hits, 3))

    # --- Reasoning & Multi-step Thinking ---
    reasoning_hits = _count_keyword_hits(full_text, REASONING_KEYWORDS)
    rea_score = _score_from_signals(reasoning_hits, 5, base=3, ceiling=9)

    # --- Creativity & Originality ---
    creativity_hits = _count_keyword_hits(full_text, CREATIVITY_KEYWORDS)
    cre_score = _score_from_signals(creativity_hits, 4, base=4, ceiling=9)

    # --- UX & Presentation ---
    ux_score = 3
    if has_repo:
        ux_score += 1
    if has_demo:
        ux_score += 2
    if len(readme) > 2000:
        ux_score += 1
    if len(readme) > 5000:
        ux_score += 1
    if setup and setup.lower() not in ("_no response_", ""):
        ux_score += 1
    ux_score = min(10, ux_score)

    # --- Technical Implementation ---
    tech_hits = _count_keyword_hits(full_text, RELIABILITY_KEYWORDS)
    tech_diversity = min(len(techs), 10)
    tech_score = _score_from_signals(tech_hits, 5, base=3, ceiling=9)
    if tech_diversity > 5:
        tech_score = min(10, tech_score + 1)

    criteria_scores = {
        "Accuracy & Relevance": acc_score,
        "Reasoning & Multi-step Thinking": rea_score,
        "Creativity & Originality": cre_score,
        "User Experience & Presentation": ux_score,
        "Technical Implementation": tech_score,
    }

    weights = {
        "Accuracy & Relevance": 0.25,
        "Reasoning & Multi-step Thinking": 0.25,
        "Creativity & Originality": 0.20,
        "User Experience & Presentation": 0.15,
        "Technical Implementation": 0.15,
    }

    weighted_total = sum(
        criteria_scores[k] * weights[k] for k in criteria_scores
    ) * 10

    return _build_score_entry(detail, criteria_scores, weighted_total, full_text)


def _evaluate_enterprise_agents(detail: dict[str, Any]) -> dict[str, Any]:
    """Score an Enterprise Agents submission."""
    readme = detail.get("readme_content") or ""
    desc = detail.get("description") or ""
    highlights = detail.get("technical_highlights") or ""
    setup = detail.get("setup_summary") or ""
    demo_desc = detail.get("demo_description") or ""
    techs = detail.get("technologies") or []
    checklist = detail.get("submission_checklist") or {}
    has_demo = detail.get("has_demo", False)
    has_repo = detail.get("repo_url") is not None

    corpus = f"{readme} {desc} {highlights} {setup} {demo_desc}".lower()
    tech_str = " ".join(techs).lower()
    full_text = f"{corpus} {tech_str}"

    # --- Technical Implementation ---
    ent_hits = _count_keyword_hits(full_text, ENTERPRISE_KEYWORDS)
    rel_hits = _count_keyword_hits(full_text, RELIABILITY_KEYWORDS)
    tech_score = 3
    if has_repo:
        tech_score += 1
    tech_score += min(ent_hits, 3)
    tech_score += min(rel_hits // 2, 2)
    tech_score = min(10, tech_score)

    # --- Business Value ---
    biz_kw = ["business", "enterprise", "roi", "productiv", "efficien",
              "automat", "workflow", "hr", "finance", "legal", "supply chain",
              "helpdesk", "it support", "sales", "customer"]
    biz_hits = _count_keyword_hits(full_text, biz_kw)
    biz_score = _score_from_signals(biz_hits, 4, base=4, ceiling=9)

    # --- Innovation & Creativity ---
    creativity_hits = _count_keyword_hits(full_text, CREATIVITY_KEYWORDS)
    innov_score = _score_from_signals(creativity_hits, 4, base=4, ceiling=9)
    if has_demo:
        innov_score = min(10, innov_score + 1)

    criteria_scores = {
        "Technical Implementation": tech_score,
        "Business Value": biz_score,
        "Innovation & Creativity": innov_score,
    }

    weights = {
        "Technical Implementation": 0.33,
        "Business Value": 0.33,
        "Innovation & Creativity": 0.34,
    }

    weighted_total = sum(
        criteria_scores[k] * weights[k] for k in criteria_scores
    ) * 10

    return _build_score_entry(detail, criteria_scores, weighted_total, full_text)


def _evaluate_unknown_track(detail: dict[str, Any]) -> dict[str, Any]:
    """Fallback scoring for unknown track — use general criteria."""
    readme = detail.get("readme_content") or ""
    desc = detail.get("description") or ""
    highlights = detail.get("technical_highlights") or ""
    techs = detail.get("technologies") or []
    has_demo = detail.get("has_demo", False)
    has_repo = detail.get("repo_url") is not None

    full_text = f"{readme} {desc} {highlights} ".lower()

    # Try to infer actual track from content
    ent_hits = _count_keyword_hits(full_text, ENTERPRISE_KEYWORDS)
    copilot_hits = _count_keyword_hits(full_text, COPILOT_MCP_KEYWORDS)

    if ent_hits > copilot_hits:
        detail_copy = dict(detail)
        detail_copy["track"] = "enterprise-agents"
        return _evaluate_enterprise_agents(detail_copy)
    else:
        detail_copy = dict(detail)
        detail_copy["track"] = "creative-apps"
        return _evaluate_creative_apps(detail_copy)


def _build_score_entry(
    detail: dict[str, Any],
    criteria_scores: dict[str, int],
    weighted_total: float,
    full_text: str,
) -> dict[str, Any]:
    """Build the score entry dict."""
    # Auto-generate strengths/improvements
    strengths = []
    improvements = []

    if detail.get("has_demo"):
        strengths.append("Demo video or screenshots provided")
    else:
        improvements.append("No demo materials provided")

    if detail.get("readme_content") and len(detail["readme_content"]) > 3000:
        strengths.append("Comprehensive README documentation")
    elif not detail.get("readme_content"):
        improvements.append("No README found or repository inaccessible")

    if detail.get("repo_url"):
        strengths.append("Public repository available")
    else:
        improvements.append("No repository URL provided")

    techs = detail.get("technologies") or []
    if len(techs) >= 5:
        strengths.append(f"Rich technology stack ({len(techs)} technologies)")

    checklist = detail.get("submission_checklist") or {}
    done = sum(1 for v in checklist.values() if v)
    if checklist and done == len(checklist):
        strengths.append("All submission checklist items completed")
    elif checklist and done < len(checklist):
        improvements.append(
            f"Incomplete checklist ({done}/{len(checklist)} items)"
        )

    high_scores = [k for k, v in criteria_scores.items() if v >= 7]
    low_scores = [k for k, v in criteria_scores.items() if v <= 4]
    for k in high_scores[:2]:
        strengths.append(f"Strong {k}")
    for k in low_scores[:2]:
        improvements.append(f"Weak {k}")

    project = detail.get("project_name") or detail.get("title", "Unknown")
    track = detail.get("track", "unknown")
    summary = (
        f"{project} is a {track.replace('-', ' ')} submission "
        f"scoring {weighted_total:.1f}/100. "
    )
    if strengths:
        summary += f"Key strengths: {', '.join(strengths[:2])}. "
    if improvements:
        summary += f"Areas for improvement: {', '.join(improvements[:2])}."

    return {
        "issue_number": detail["issue_number"],
        "project_name": project,
        "track": track,
        "github_username": detail.get("github_username"),
        "issue_url": detail.get("issue_url", ""),
        "repo_url": detail.get("repo_url"),
        "criteria_scores": criteria_scores,
        "weighted_total": round(weighted_total, 1),
        "strengths": strengths[:5],
        "improvements": improvements[:5],
        "summary": summary,
    }


EVALUATORS = {
    "creative-apps": _evaluate_creative_apps,
    "reasoning-agents": _evaluate_reasoning_agents,
    "enterprise-agents": _evaluate_enterprise_agents,
    "unknown": _evaluate_unknown_track,
}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_scoring_pipeline():
    """Execute the full scoring pipeline."""
    from saiten_mcp.tools.submissions import list_submissions, get_submission_detail
    from saiten_mcp.tools.scores import save_scores
    from saiten_mcp.tools.reports import generate_ranking_report
    from saiten_mcp.server import rate_limiter

    # Batch scoring calls get_submission_detail many times in a short burst.
    # Raise the per-minute allowance to avoid false-positive local throttling.
    rate_limiter.max_calls = max(rate_limiter.max_calls, 150)

    async def get_detail_with_retry(issue_num: int, max_attempts: int = 3) -> dict[str, Any]:
        """Fetch submission detail with retry when local rate limiter is hit."""
        for attempt in range(1, max_attempts + 1):
            try:
                return await get_submission_detail(issue_num)
            except ValueError as exc:
                msg = str(exc)
                is_rate_limited = "Rate limit exceeded for 'get_submission_detail'" in msg
                if is_rate_limited and attempt < max_attempts:
                    wait_seconds = 61
                    logger.warning(
                        "    Rate-limited on #%d; waiting %ds before retry (%d/%d)",
                        issue_num,
                        wait_seconds,
                        attempt,
                        max_attempts,
                    )
                    await asyncio.sleep(wait_seconds)
                    continue
                raise

        raise RuntimeError(f"Failed to fetch detail after retries: #{issue_num}")

    # 1. Fetch all submissions
    logger.info("=" * 60)
    logger.info("STEP 1: Fetching submission list...")
    logger.info("=" * 60)
    submissions = await list_submissions(state="all")
    logger.info(f"  Found {len(submissions)} submissions")

    tracks = {}
    for s in submissions:
        t = s["track"]
        tracks[t] = tracks.get(t, 0) + 1
    logger.info(f"  Distribution: {tracks}")

    # 2. Score each submission
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Scoring submissions...")
    logger.info("=" * 60)

    all_scores: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for i, sub in enumerate(submissions, 1):
        issue_num = sub["issue_number"]
        project = sub["project_name"][:40]
        track = sub["track"]
        logger.info(f"  [{i:2d}/{len(submissions)}] #{issue_num} ({track}) {project}")

        try:
            detail = await get_detail_with_retry(issue_num)
            # Use actual track from detail (may differ from list)
            actual_track = detail.get("track", track)
            evaluator = EVALUATORS.get(actual_track, _evaluate_unknown_track)
            score_entry = evaluator(detail)
            all_scores.append(score_entry)
            logger.info(f"           -> {score_entry['weighted_total']:.1f}/100")
        except Exception as exc:
            logger.warning(f"           -> SKIPPED: {exc}")
            errors.append({"issue_number": issue_num, "error": str(exc)})

    logger.info(f"\n  Scored: {len(all_scores)}, Errors: {len(errors)}")

    # 3. Save scores
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Saving scores...")
    logger.info("=" * 60)
    result = await save_scores(all_scores)
    logger.info(
        f"  New: {result['saved_count']}, Updated: {result['updated_count']}, "
        f"Total: {result['total_in_store']}"
    )

    # 4. Generate ranking report
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Generating ranking report...")
    logger.info("=" * 60)
    report = await generate_ranking_report(top_n=10)
    logger.info(f"  Report: {report['report_path']}")
    logger.info(f"  Total scored: {report['total_scored']}")

    # 5. Print Top 10
    logger.info("\n" + "=" * 60)
    logger.info("🏆 TOP 10 RESULTS")
    logger.info("=" * 60)
    for entry in report["top_entries"]:
        rank = entry["rank"]
        name = entry["project_name"][:45]
        track = entry["track"]
        score = entry["score"]
        emoji = {"creative-apps": "🎨", "reasoning-agents": "🧠",
                 "enterprise-agents": "💼"}.get(track, "❓")
        logger.info(f"  {rank:2d}. {emoji} {name:<45s} {score:5.1f}")

    if errors:
        logger.info(f"\n⚠️  Skipped {len(errors)} submissions due to errors:")
        for e in errors:
            logger.info(f"  - #{e['issue_number']}: {e['error'][:80]}")

    logger.info("\n✅ Pipeline complete!")


if __name__ == "__main__":
    asyncio.run(run_scoring_pipeline())
