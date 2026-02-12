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

    merged, updated_count = _merge_scores(existing, scores)
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
