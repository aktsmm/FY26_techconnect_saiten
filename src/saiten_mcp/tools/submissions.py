"""Saiten MCP — 提出物 (Submissions) ツール.

GitHub Issues から Agents League @ TechConnect の提出物情報を取得・パースする。
gh CLI を asyncio.create_subprocess_exec 経由で呼び出す。
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any

from saiten_mcp.server import mcp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
REPO = "microsoft/agentsleague-techconnect"
MIN_ISSUE_NUMBER = 10  # #1〜#9 はリポジトリ管理用

TRACK_LABEL_MAP: dict[str, str] = {
    "Creative Apps": "creative-apps",
    "🎨 Creative Apps": "creative-apps",
    "Reasoning Agents": "reasoning-agents",
    "🧠 Reasoning Agents": "reasoning-agents",
    "Enterprise Agents": "enterprise-agents",
    "💼 Enterprise Agents": "enterprise-agents",
}

TRACK_BODY_MAP: dict[str, str] = {
    "Creative Apps - GitHub Copilot": "creative-apps",
    "Reasoning Agents - Microsoft Foundry": "reasoning-agents",
    "Enterprise Agents - M365 Agents Toolkit": "enterprise-agents",
}

# Issue 本文のセクション定義（パーサー関数のマッピング）
SECTION_PARSERS: dict[str, str] = {
    "Track": "parse_track",
    "Project Name": "parse_text",
    "Microsoft Alias": "_pii",
    "GitHub Username": "_pii",
    "Repository URL": "parse_url",
    "Project Description": "parse_text",
    "Demo Video or Screenshots": "parse_demo",
    "Primary Programming Language": "parse_text",
    "Key Technologies Used": "parse_list",
    "Submission Requirements": "parse_checklist",
    "Technical Highlights": "parse_text",
    "Quick Setup Summary": "parse_text",
    "Team Members (if any)": "parse_text",
}


# ---------------------------------------------------------------------------
# gh CLI ヘルパー
# ---------------------------------------------------------------------------
async def _run_gh(*args: str) -> str:
    """gh コマンドを実行し stdout を返す。失敗時は例外を送出する (Fail Fast)."""
    proc = await asyncio.create_subprocess_exec(
        "gh", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode().strip() if stderr else "unknown error"
        raise RuntimeError(
            f"gh コマンド失敗 (exit={proc.returncode}): gh {' '.join(args)}\n{err_msg}"
        )
    return stdout.decode()


# ---------------------------------------------------------------------------
# パーサーヘルパー
# ---------------------------------------------------------------------------
def _parse_sections(body: str) -> dict[str, str]:
    """Issue 本文を ``### セクション名`` で分割し {セクション名: 内容} を返す."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    lines: list[str] = []

    for line in body.splitlines():
        header_match = re.match(r"^###\s+(.+)$", line)
        if header_match:
            if current_key is not None:
                sections[current_key] = "\n".join(lines).strip()
            current_key = header_match.group(1).strip()
            lines = []
        else:
            lines.append(line)

    # 最後のセクション
    if current_key is not None:
        sections[current_key] = "\n".join(lines).strip()

    return sections


def parse_text(value: str) -> str:
    """テキストをそのまま返す（前後空白除去済み）."""
    return value.strip()


def parse_url(value: str) -> str | None:
    """URL を抽出する。見つからなければ None."""
    value = value.strip()
    match = re.search(r"https?://[^\s\)>]+", value)
    return match.group(0) if match else (value if value.startswith("http") else None)


def parse_track(value: str) -> str:
    """Track セクションの値からトラック ID を判定する."""
    value_stripped = value.strip()
    for body_key, track_id in TRACK_BODY_MAP.items():
        if body_key in value_stripped:
            return track_id
    # フォールバック: ラベルマップのキーも試す
    for label_key, track_id in TRACK_LABEL_MAP.items():
        if label_key in value_stripped:
            return track_id
    return "unknown"


def parse_list(value: str) -> list[str]:
    """カンマ区切り・改行区切りのリストをパースする."""
    items: list[str] = []
    for line in value.splitlines():
        line = line.strip().lstrip("-").lstrip("*").strip()
        if not line or line == "_No response_":
            continue
        # カンマ区切りも展開
        for part in line.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items


def parse_checklist(value: str) -> dict[str, bool]:
    """チェックリスト (``- [x]`` / ``- [ ]``) をパースする."""
    result: dict[str, bool] = {}
    for line in value.splitlines():
        match = re.match(r"^\s*-\s*\[([ xX])\]\s*(.+)$", line)
        if match:
            checked = match.group(1).lower() == "x"
            label = match.group(2).strip()
            result[label] = checked
    return result


def parse_demo(value: str) -> tuple[bool, str]:
    """Demo セクションから (has_demo, description) を返す."""
    stripped = value.strip()
    if not stripped or stripped == "_No response_":
        return False, ""
    # URL やイメージリンクが含まれていれば has_demo=True
    has_url = bool(re.search(r"https?://[^\s]+", stripped))
    has_image = bool(re.search(r"!\[.*?\]\(.*?\)", stripped))
    has_demo = has_url or has_image
    return has_demo, stripped


# ---------------------------------------------------------------------------
# トラック判定
# ---------------------------------------------------------------------------
def _detect_track_from_labels(labels: list) -> str | None:
    """ラベル一覧からトラック ID を返す。見つからなければ None."""
    for label in labels:
        # jq フィルタ済みの場合は文字列、未加工の場合は dict
        name = label if isinstance(label, str) else label.get("name", "")
        if name in TRACK_LABEL_MAP:
            return TRACK_LABEL_MAP[name]
    return None


def _detect_track_from_body(body: str) -> str:
    """Issue 本文の Track セクションからトラック ID を返す."""
    sections = _parse_sections(body)
    track_value = sections.get("Track", "")
    return parse_track(track_value)


def _detect_track(issue: dict[str, Any]) -> str:
    """ラベル優先 → 本文フォールバックでトラック ID を返す."""
    labels = issue.get("labels", [])
    track = _detect_track_from_labels(labels)
    if track:
        return track
    body = issue.get("body") or ""
    return _detect_track_from_body(body)


# ---------------------------------------------------------------------------
# README 取得
# ---------------------------------------------------------------------------
async def _fetch_readme(repo_url: str | None) -> str | None:
    """GitHub リポジトリの README を取得する。失敗時は None."""
    if not repo_url:
        return None

    match = re.match(r"https?://github\.com/([^/]+)/([^/\s?#]+)", repo_url)
    if not match:
        return None

    owner, repo = match.group(1), match.group(2).rstrip("/")
    try:
        raw = await _run_gh(
            "api", f"repos/{owner}/{repo}/readme",
            "--jq", ".content",
        )
        content_b64 = raw.strip().replace("\n", "")
        content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        # 最大 10,000 文字にトリム
        if len(content) > 10_000:
            content = content[:10_000] + "\n\n... (10,000 文字でトリム)"
        return content
    except Exception:
        logger.warning("README 取得失敗: %s/%s", owner, repo, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# プロジェクト名抽出ヘルパー
# ---------------------------------------------------------------------------
def _extract_project_name(issue: dict[str, Any]) -> str:
    """Issue 本文から Project Name を抽出する。なければ title を返す."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    name = sections.get("Project Name", "").strip()
    if name and name != "_No response_":
        return name
    return issue.get("title", "")


# ---------------------------------------------------------------------------
# has_demo 判定ヘルパー
# ---------------------------------------------------------------------------
def _extract_has_demo(issue: dict[str, Any]) -> bool:
    """Issue 本文の Demo セクションから has_demo を判定する."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    demo_value = sections.get("Demo Video or Screenshots", "")
    has_demo, _ = parse_demo(demo_value)
    return has_demo


# ---------------------------------------------------------------------------
# repo_url 抽出ヘルパー
# ---------------------------------------------------------------------------
def _extract_repo_url(issue: dict[str, Any]) -> str | None:
    """Issue 本文から Repository URL を抽出する."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    url_value = sections.get("Repository URL", "")
    return parse_url(url_value)


# ---------------------------------------------------------------------------
# ツール: list_submissions
# ---------------------------------------------------------------------------
@mcp.tool()
async def list_submissions(
    track: str | None = None,
    state: str = "all",
) -> list[dict]:
    """Agents League の提出物一覧を取得する。

    Args:
        track: フィルタするトラック名。
            ``"creative-apps"`` | ``"reasoning-agents"`` | ``"enterprise-agents"`` | None (全件)
        state: Issue の状態。``"open"`` | ``"closed"`` | ``"all"``

    Returns:
        提出物サマリーのリスト。各要素は issue_number, title, track,
        project_name, repo_url, created_at, has_demo を含む辞書。

    Raises:
        RuntimeError: gh コマンド実行失敗時。
    """
    # jq フィルタ: 必要なフィールドだけ抽出
    jq_filter = (
        "[.[] | {number, title, body, labels: [.labels[].name], created_at}]"
    )

    args = [
        "api", f"repos/{REPO}/issues",
        "--method", "GET",
        "--paginate",
        "-q", jq_filter,
    ]

    # state パラメータ
    if state in ("open", "closed"):
        args.extend(["-f", f"state={state}"])
    else:
        args.extend(["-f", "state=all"])

    # per_page を最大に
    args.extend(["-F", "per_page=100"])

    raw = await _run_gh(*args)

    # --paginate は JSON 配列を複数返すことがあるため結合
    all_issues: list[dict[str, Any]] = []
    for chunk in _split_json_arrays(raw):
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, list):
                all_issues.extend(parsed)
            else:
                all_issues.append(parsed)
        except json.JSONDecodeError as exc:
            logger.warning("JSON パース失敗 (スキップ): %s", exc)

    results: list[dict[str, Any]] = []
    for issue in all_issues:
        issue_number = issue.get("number", 0)
        if issue_number < MIN_ISSUE_NUMBER:
            continue

        detected_track = _detect_track(issue)

        # トラックフィルタ
        if track is not None and detected_track != track:
            continue

        try:
            entry = {
                "issue_number": issue_number,
                "title": issue.get("title", ""),
                "track": detected_track,
                "project_name": _extract_project_name(issue),
                "repo_url": _extract_repo_url(issue),
                "created_at": issue.get("created_at", ""),
                "has_demo": _extract_has_demo(issue),
            }
            results.append(entry)
        except Exception:
            logger.warning(
                "Issue #%d のパースに失敗しました。スキップします。",
                issue_number,
                exc_info=True,
            )

    logger.info("list_submissions: %d 件取得 (track=%s, state=%s)", len(results), track, state)
    return results


# ---------------------------------------------------------------------------
# ツール: get_submission_detail
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_submission_detail(issue_number: int) -> dict:
    """指定 Issue 番号の提出物詳細を取得する。

    Issue テンプレートの各セクションをパースし、採点用データを返す。
    GitHub Username は採点バイアス排除のため採点時は非表示にするが、
    レポート出力用に github_username フィールドとして保持する。
    repo_url が GitHub リポジトリの場合、README も取得する。

    Args:
        issue_number: 取得する Issue 番号。

    Returns:
        提出物の詳細情報を含む辞書。

    Raises:
        RuntimeError: gh コマンド実行失敗時。
    """
    raw = await _run_gh(
        "api", f"repos/{REPO}/issues/{issue_number}",
    )
    issue: dict[str, Any] = json.loads(raw)

    body = issue.get("body") or ""
    sections = _parse_sections(body)

    # トラック判定
    track_id = _detect_track(issue)

    # 各セクションをパース
    project_name = parse_text(sections.get("Project Name", ""))
    if not project_name or project_name == "_No response_":
        project_name = issue.get("title", "")

    description = parse_text(sections.get("Project Description", ""))
    repo_url = parse_url(sections.get("Repository URL", ""))
    has_demo, demo_description = parse_demo(
        sections.get("Demo Video or Screenshots", "")
    )
    technologies = parse_list(sections.get("Key Technologies Used", ""))
    checklist = parse_checklist(sections.get("Submission Requirements", ""))
    technical_highlights = parse_text(
        sections.get("Technical Highlights", "")
    )
    setup_summary = parse_text(sections.get("Quick Setup Summary", ""))
    team_members_raw = parse_text(sections.get("Team Members (if any)", ""))
    team_members = team_members_raw if team_members_raw and team_members_raw != "_No response_" else None

    # GitHub Username (for report display, NOT for scoring bias)
    github_username_raw = parse_text(sections.get("GitHub Username", ""))
    github_username = github_username_raw if github_username_raw and github_username_raw != "_No response_" else None

    # Issue URL for linking
    issue_url = f"https://github.com/{REPO}/issues/{issue_number}"

    # README 取得
    readme_content = await _fetch_readme(repo_url)

    result: dict[str, Any] = {
        "issue_number": issue.get("number", issue_number),
        "title": issue.get("title", ""),
        "track": track_id,
        "project_name": project_name,
        "description": description,
        "repo_url": repo_url,
        "issue_url": issue_url,
        "github_username": github_username,
        "readme_content": readme_content,
        "technologies": technologies,
        "technical_highlights": technical_highlights,
        "has_demo": has_demo,
        "demo_description": demo_description,
        "submission_checklist": checklist,
        "team_members": team_members,
        "setup_summary": setup_summary,
    }

    logger.info(
        "get_submission_detail: Issue #%d (%s) track=%s",
        issue_number,
        project_name,
        track_id,
    )
    return result


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
def _split_json_arrays(raw: str) -> list[str]:
    """``--paginate`` が返す連結 JSON 配列を分割する.

    gh の ``--paginate`` は複数の JSON 配列を改行区切りで返すことがあるため、
    ブラケットの深さを追跡して個別の配列に分割する。
    """
    chunks: list[str] = []
    depth = 0
    start = -1

    for i, ch in enumerate(raw):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start >= 0:
                chunks.append(raw[start : i + 1])
                start = -1

    # JSON 配列が見つからなかった場合は raw 全体を返す
    if not chunks and raw.strip():
        chunks.append(raw.strip())

    return chunks
