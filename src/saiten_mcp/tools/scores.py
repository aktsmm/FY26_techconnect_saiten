"""Saiten MCP — Scores persistence tool.

Persists scoring results to data/scores.json with idempotent
merge (existing scores are overwritten by issue_number).
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from typing import Any

from saiten_mcp.server import mcp, DATA_DIR

logger = logging.getLogger(__name__)

SCORES_FILE = DATA_DIR / "scores.json"


def _load_scores() -> dict[str, Any]:
    """Load scores.json. Returns an empty store if file does not exist."""
    if not SCORES_FILE.exists():
        return {
            "metadata": {
                "last_updated": "",
                "version": "1.0",
                "total_submissions": 0,
                "scored_count": 0,
            },
            "scores": [],
        }

    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        # Create backup of corrupted file before resetting
        logger.warning("Failed to load scores.json. Creating backup: %s", exc)
        backup_path = SCORES_FILE.with_suffix(".json.bak")
        try:
            shutil.copy2(SCORES_FILE, backup_path)
            logger.info("Backup created: %s", backup_path)
        except OSError:
            pass
        return {
            "metadata": {
                "last_updated": "",
                "version": "1.0",
                "total_submissions": 0,
                "scored_count": 0,
            },
            "scores": [],
        }


def _save_scores(store: dict[str, Any]) -> None:
    """Write store to scores.json."""
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _merge_scores(
    existing: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Merge new scores into existing scores (idempotent).

    Uses issue_number as key; existing entries are overwritten.

    Returns:
        (merged list, number of overwrites)
    """
    score_map: dict[int, dict[str, Any]] = {
        s["issue_number"]: s for s in existing
    }
    updated_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for s in new:
        issue_num = s["issue_number"]
        s["scored_at"] = now
        if issue_num in score_map:
            updated_count += 1
        score_map[issue_num] = s

    merged = sorted(
        score_map.values(),
        key=lambda x: x.get("weighted_total", 0),
        reverse=True,
    )
    return merged, updated_count


@mcp.tool()
async def save_scores(scores: list[dict]) -> dict[str, Any]:
    """Save scoring results to data/scores.json.

    Existing scores for the same Issue are overwritten (idempotent).
    New Issues are appended.

    Args:
        scores: List of scoring result dicts. Each must contain:
            - issue_number (int)
            - project_name (str)
            - track (str)
            - criteria_scores (dict[str, int]): per-criterion scores (1-10)
            - weighted_total (float): weighted total (0-100)
            - evidence (dict[str, str]): per-criterion evidence citations
            - confidence (str): 'high', 'medium', or 'low'
            - red_flags_detected (list[str]): red flag signals found
            - bonus_signals_detected (list[str]): bonus signals found
            - strengths (list[str])
            - improvements (list[str])
            - summary (str)

    Returns:
        Summary dict (saved_count, updated_count, total_in_store, file_path).

    Raises:
        OSError: If disk write fails.
    """
    store = _load_scores()
    existing = store.get("scores", [])

    # --- Input Validation (Fail Fast) ---
    validated: list[dict[str, Any]] = []
    for i, s in enumerate(scores):
        issue_num = s.get("issue_number")
        if not isinstance(issue_num, int) or issue_num < 1:
            raise ValueError(
                f"scores[{i}]: issue_number must be a positive int, got {issue_num!r}"
            )
        if not s.get("project_name"):
            raise ValueError(f"scores[{i}] (#{issue_num}): project_name is required")
        if not s.get("track"):
            raise ValueError(f"scores[{i}] (#{issue_num}): track is required")

        total = s.get("weighted_total", -1)
        if not isinstance(total, (int, float)) or not (0 <= total <= 100):
            raise ValueError(
                f"scores[{i}] (#{issue_num}): weighted_total must be 0-100, got {total}"
            )

        criteria = s.get("criteria_scores", {})
        if not isinstance(criteria, dict):
            raise ValueError(
                f"scores[{i}] (#{issue_num}): criteria_scores must be a dict"
            )
        for crit_name, crit_val in criteria.items():
            if not isinstance(crit_val, int) or not (1 <= crit_val <= 10):
                raise ValueError(
                    f"scores[{i}] (#{issue_num}): criteria '{crit_name}' "
                    f"must be 1-10, got {crit_val}"
                )

        validated.append(s)

    merged, updated_count = _merge_scores(existing, validated)
    new_count = len(scores) - updated_count

    store["scores"] = merged
    store["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    store["metadata"]["scored_count"] = len(merged)

    _save_scores(store)

    result = {
        "saved_count": new_count,
        "updated_count": updated_count,
        "total_in_store": len(merged),
        "file_path": str(SCORES_FILE),
    }

    logger.info(
        "save_scores: new=%d, updated=%d, total=%d",
        new_count,
        updated_count,
        len(merged),
    )
    return result


@mcp.tool()
async def adjust_scores(
    adjustments: list[dict],
) -> dict[str, Any]:
    """Apply qualitative AI-reviewed adjustments to existing scores.

    Used by the scoring agent AFTER mechanical baseline scoring.
    The agent reads each submission's content, reviews the baseline
    scores, and applies qualitative adjustments with justification.

    Each adjustment can modify criteria_scores, summary, strengths,
    improvements, and/or weighted_total. Fields not provided are
    kept as-is from the existing score.

    Args:
        adjustments: List of adjustment dicts. Each must contain:
            - issue_number (int): the submission to adjust
            - ai_review_notes (str): agent's qualitative assessment
            And optionally any of:
            - criteria_scores (dict[str, int]): adjusted per-criterion scores
            - weighted_total (float): adjusted total (auto-recalculated if
              criteria_scores changed and weighted_total not provided)
            - summary (str): improved qualitative summary
            - strengths (list[str]): refined strengths
            - improvements (list[str]): refined improvements
            - confidence (str): updated confidence level

    Returns:
        Summary dict (adjusted_count, skipped, details).
    """
    store = _load_scores()
    existing = store.get("scores", [])
    score_map: dict[int, dict[str, Any]] = {
        s["issue_number"]: s for s in existing
    }

    adjusted_count = 0
    skipped: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for adj in adjustments:
        issue_num = adj.get("issue_number")
        if not isinstance(issue_num, int) or issue_num not in score_map:
            skipped.append({
                "issue_number": issue_num,
                "reason": "Not found in existing scores",
            })
            continue

        entry = score_map[issue_num]
        old_total = entry.get("weighted_total", 0)
        changes: list[str] = []

        # Apply criteria_scores adjustments
        if "criteria_scores" in adj:
            new_criteria = adj["criteria_scores"]
            old_criteria = entry.get("criteria_scores", {})
            for crit, val in new_criteria.items():
                if not isinstance(val, int) or not (1 <= val <= 10):
                    skipped.append({
                        "issue_number": issue_num,
                        "reason": f"Invalid score for {crit}: {val}",
                    })
                    continue
                if old_criteria.get(crit) != val:
                    changes.append(
                        f"{crit}: {old_criteria.get(crit, '?')} -> {val}"
                    )
            entry["criteria_scores"].update(new_criteria)

        # Recalculate weighted_total if criteria changed but total not given
        if "criteria_scores" in adj and "weighted_total" not in adj:
            track = entry.get("track", "")
            if track == "creative-apps":
                weights = {
                    "Accuracy & Relevance": 0.222,
                    "Reasoning & Multi-step Thinking": 0.222,
                    "Creativity & Originality": 0.167,
                    "UX & Presentation": 0.167,
                    "Reliability & Safety": 0.222,
                }
            elif track == "reasoning-agents":
                weights = {
                    "Accuracy & Relevance": 0.25,
                    "Reasoning & Multi-step Thinking": 0.25,
                    "Creativity & Originality": 0.2,
                    "User Experience & Presentation": 0.15,
                    "Technical Implementation": 0.15,
                }
            elif track == "enterprise-agents":
                weights = {
                    "Technical Implementation": 0.33,
                    "Business Value": 0.33,
                    "Innovation & Creativity": 0.34,
                }
            else:
                weights = {}

            if weights:
                cs = entry["criteria_scores"]
                total = round(
                    sum(cs.get(c, 5) * w for c, w in weights.items()) * 10,
                    1,
                )
                entry["weighted_total"] = total
                changes.append(f"weighted_total: {old_total} -> {total}")

        # Apply explicit weighted_total
        if "weighted_total" in adj:
            new_total = adj["weighted_total"]
            if isinstance(new_total, (int, float)) and 0 <= new_total <= 100:
                entry["weighted_total"] = round(float(new_total), 1)
                changes.append(f"weighted_total: {old_total} -> {new_total}")

        # Apply qualitative fields
        for field in ("summary", "strengths", "improvements", "confidence"):
            if field in adj:
                entry[field] = adj[field]
                changes.append(f"{field} updated")

        # Store AI review notes
        review_notes = adj.get("ai_review_notes", "")
        if review_notes:
            entry["ai_review_notes"] = review_notes
            entry["ai_reviewed"] = True

        if changes:
            adjusted_count += 1
            details.append({
                "issue_number": issue_num,
                "project_name": entry.get("project_name", ""),
                "changes": changes,
                "new_total": entry.get("weighted_total"),
            })

    # Re-sort and save
    store["scores"] = sorted(
        score_map.values(),
        key=lambda x: x.get("weighted_total", 0),
        reverse=True,
    )
    store["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_scores(store)

    logger.info("adjust_scores: adjusted=%d, skipped=%d", adjusted_count, len(skipped))

    return {
        "adjusted_count": adjusted_count,
        "skipped": skipped,
        "details": details,
    }
