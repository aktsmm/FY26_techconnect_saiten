"""Saiten MCP — スコア永続化 (Scores) ツール.

採点結果を data/scores.json に保存する。冪等性を保証し、
既存スコアは上書き方式で更新する。
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
    """scores.json を読み込む。存在しない場合は空のストアを返す."""
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
        # 破損時はバックアップ作成後に新規作成
        logger.warning("scores.json 読み込み失敗。バックアップを作成します: %s", exc)
        backup_path = SCORES_FILE.with_suffix(".json.bak")
        try:
            shutil.copy2(SCORES_FILE, backup_path)
            logger.info("バックアップ作成: %s", backup_path)
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
    """scores.json に書き込む."""
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _merge_scores(
    existing: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """既存スコアに新規スコアをマージする (冪等性保証).

    issue_number をキーとして上書き。新規は追加。

    Returns:
        (マージ済みリスト, 上書き件数)
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
    """採点結果を data/scores.json に保存する。

    既存スコアがある Issue は上書き（冪等性保証）。
    新規 Issue は追加される。

    Args:
        scores: 採点結果のリスト。各要素は以下のキーを含む辞書:
            - issue_number (int)
            - project_name (str)
            - track (str)
            - criteria_scores (dict[str, int]): 各基準のスコア (1-10)
            - weighted_total (float): 加重合計 (0-100)
            - strengths (list[str])
            - improvements (list[str])
            - summary (str)

    Returns:
        保存結果の要約辞書 (saved_count, updated_count, total_in_store, file_path)。

    Raises:
        OSError: ディスク書き込み失敗時。
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
        "save_scores: 新規=%d, 上書き=%d, 合計=%d",
        new_count,
        updated_count,
        len(merged),
    )
    return result
