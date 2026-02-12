"""Saiten MCP — Rubrics tool.

Loads track-specific YAML scoring rubric files.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from saiten_mcp.server import mcp, DATA_DIR

logger = logging.getLogger(__name__)

RUBRICS_DIR = DATA_DIR / "rubrics"

VALID_TRACKS = {"creative-apps", "reasoning-agents", "enterprise-agents"}


@mcp.tool()
async def get_scoring_rubric(track: str) -> dict[str, Any]:
    """Return the scoring rubric for the specified track.

    Loads the YAML file ``data/rubrics/{track}.yaml`` and returns
    the scoring criteria (name, weight, description, scoring_guide).

    Args:
        track: Track name. ``"creative-apps"`` | ``"reasoning-agents"``
            | ``"enterprise-agents"``

    Returns:
        Rubric dict with track, track_display_name, criteria (list),
        total_weight, score_range, and notes.

    Raises:
        FileNotFoundError: If the YAML file for the track does not exist.
        ValueError: If the track name is invalid.
    """
    if track not in VALID_TRACKS:
        available = sorted(VALID_TRACKS)
        raise ValueError(
            f"Invalid track name: '{track}'. "
            f"Available tracks: {available}"
        )

    yaml_path = RUBRICS_DIR / f"{track}.yaml"
    if not yaml_path.exists():
        available_files = [f.stem for f in RUBRICS_DIR.glob("*.yaml")]
        raise FileNotFoundError(
            f"Rubric file not found: {yaml_path}\n"
            f"Available files: {available_files}"
        )

    with open(yaml_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    # Calculate total weight
    criteria = data.get("criteria", [])
    total_weight = sum(c.get("weight", 0.0) for c in criteria)

    result: dict[str, Any] = {
        "track": data.get("track", track),
        "track_display_name": data.get("track_display_name", track),
        "criteria": criteria,
        "total_weight": round(total_weight, 3),
        "score_range": {"min": 1, "max": 10},
        "notes": data.get("notes", ""),
    }

    logger.info("get_scoring_rubric: track=%s, criteria=%d", track, len(criteria))
    return result
