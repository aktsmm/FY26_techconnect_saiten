"""Saiten MCP — レポート生成 (Reports) ツール.

data/scores.json の採点結果から Markdown ランキングレポートを生成し、
reports/ ディレクトリに出力する。
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
    """scores.json を読み込む。存在しない・空の場合は空ストアを返す."""
    if not SCORES_FILE.exists():
        logger.warning("scores.json が見つかりません: %s", SCORES_FILE)
        return {"metadata": {}, "scores": []}

    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("scores.json の読み込みに失敗しました: %s", exc)
        return {"metadata": {}, "scores": []}

    if not isinstance(data, dict):
        logger.warning("scores.json のフォーマットが不正です")
        return {"metadata": {}, "scores": []}

    return data


def _fmt_score(score: float | int) -> str:
    """スコアを小数第 1 位までフォーマットする."""
    return f"{float(score):.1f}"


def _build_ranking_md(
    scores: list[dict[str, Any]],
    metadata: dict[str, Any],
    top_n: int,
) -> str:
    """Markdown ランキングレポートを組み立てる."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    scored_count = metadata.get("scored_count", len(scores))
    total_submissions = metadata.get("total_submissions", len(scores))

    lines: list[str] = []

    # --- ヘッダー ---
    lines.append("# 🏆 Agents League @ TechConnect — 採点ランキング")
    lines.append("")
    lines.append(f"> 自動生成: {timestamp}")
    lines.append(f"> 採点済み: {scored_count} / {total_submissions} 件")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Top N ---
    top_entries = scores[:top_n]
    lines.append(f"## 🥇 Top {top_n}")
    lines.append("")
    lines.append("| 順位 | Project | Track | Submitter | 総合スコア |")
    lines.append("|------|---------|-------|-----------|------------|")
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

    # --- トラック別 Top 3 ---
    lines.append("## 🏅 トラック別 Top 3")
    lines.append("")

    for track_key in ["creative-apps", "reasoning-agents", "enterprise-agents"]:
        emoji = TRACK_EMOJI.get(track_key, "")
        display = TRACK_DISPLAY.get(track_key, track_key)
        lines.append(f"### {emoji} {display}")
        lines.append("")
        lines.append("| 順位 | Project | Submitter | 総合スコア |")
        lines.append("|------|---------|-----------|------------|")

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

    # --- 全提出物スコア一覧 ---
    lines.append("## 📊 全提出物スコア一覧")
    lines.append("")
    lines.append("| # | Issue | Project | Track | Submitter | Score | 評価日 |")
    lines.append("|---|-------|---------|-------|-----------|-------|--------|")

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

    # --- 個別評価サマリー ---
    lines.append("## 📋 個別評価サマリー")
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

        strengths = "、".join(strengths_list) if strengths_list else "—"
        improvements = "、".join(improvements_list) if improvements_list else "—"

        lines.append(f"### #{issue}: {name}")
        lines.append(f"- **トラック**: {emoji} {display}")
        lines.append(f"- **スコア**: {score}/100")
        lines.append(f"- **強み**: {strengths}")
        lines.append(f"- **改善点**: {improvements}")
        lines.append(f"- **総評**: {summary}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def generate_ranking_report(
    top_n: int = 10,
) -> dict[str, Any]:
    """ランキングレポートを Markdown で生成し reports/ranking.md に出力する。

    data/scores.json の採点結果を読み込み、総合順位・トラック別順位・
    個別評価サマリーを含むレポートを自動生成する。

    Args:
        top_n: 上位何件を Top セクションに強調表示するか（デフォルト: 10）。

    Returns:
        生成結果の辞書 (report_path, total_scored, top_n, top_entries)。
    """
    store = _load_scores()
    scores: list[dict[str, Any]] = store.get("scores", [])
    metadata: dict[str, Any] = store.get("metadata", {})

    if not scores:
        logger.info("採点データがありません。空のレポートを生成します。")

    # weighted_total で降順ソート（保険: 保存時にもソート済み）
    scores.sort(key=lambda x: x.get("weighted_total", 0), reverse=True)

    # Markdown 生成
    md_content = _build_ranking_md(scores, metadata, top_n)

    # ファイル出力
    report_path = REPORTS_DIR / "ranking.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info("ランキングレポートを生成しました: %s", report_path)

    # Top N サマリーを返却用に構築
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
