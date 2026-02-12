"""Saiten MCP — 採点基準 (Rubrics) ツール.

トラック別の YAML 採点基準ファイルを読み込んで返す。
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
    """指定トラックの採点基準を返す。

    YAML ファイル ``data/rubrics/{track}.yaml`` を読み込み、
    採点基準（各項目の名前・重み・説明・スコアリングガイド）を返す。

    Args:
        track: トラック名。``"creative-apps"`` | ``"reasoning-agents"``
            | ``"enterprise-agents"``

    Returns:
        採点基準辞書。track, track_display_name, criteria (リスト),
        total_weight, score_range, notes を含む。

    Raises:
        FileNotFoundError: 指定トラックの YAML ファイルが存在しない場合。
        ValueError: track 名が不正な場合。
    """
    if track not in VALID_TRACKS:
        available = sorted(VALID_TRACKS)
        raise ValueError(
            f"不正なトラック名: '{track}'. "
            f"利用可能なトラック: {available}"
        )

    yaml_path = RUBRICS_DIR / f"{track}.yaml"
    if not yaml_path.exists():
        available_files = [f.stem for f in RUBRICS_DIR.glob("*.yaml")]
        raise FileNotFoundError(
            f"採点基準ファイルが見つかりません: {yaml_path}\n"
            f"利用可能なファイル: {available_files}"
        )

    with open(yaml_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    # 重みの合計を計算
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

    logger.info("get_scoring_rubric: track=%s, criteria=%d 件", track, len(criteria))
    return result
