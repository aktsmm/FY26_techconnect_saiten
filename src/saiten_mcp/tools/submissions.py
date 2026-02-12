"""Saiten MCP — Submissions tool.

Fetches and parses Agents League @ TechConnect submission data
from GitHub Issues via gh CLI (asyncio.create_subprocess_exec).
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
# Constants
# ---------------------------------------------------------------------------
REPO = "microsoft/agentsleague-techconnect"
MIN_ISSUE_NUMBER = 10  # #1-#9 are reserved for repository management

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

# Issue body section definitions (parser function mapping)
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
# gh CLI helpers
# ---------------------------------------------------------------------------
async def _run_gh(*args: str) -> str:
    """Execute a gh command and return stdout. Raises an exception on failure (Fail Fast)."""
    proc = await asyncio.create_subprocess_exec(
        "gh", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode().strip() if stderr else "unknown error"
        raise RuntimeError(
            f"gh command failed (exit={proc.returncode}): gh {' '.join(args)}\n{err_msg}"
        )
    return stdout.decode()


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------
def _parse_sections(body: str) -> dict[str, str]:
    """Split Issue body by ``### Section Name`` headers and return {section_name: content}."""
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

    # Last section
    if current_key is not None:
        sections[current_key] = "\n".join(lines).strip()

    return sections


def parse_text(value: str) -> str:
    """Return text as-is (with leading/trailing whitespace stripped)."""
    return value.strip()


def parse_url(value: str) -> str | None:
    """Extract a URL. Returns None if not found."""
    value = value.strip()
    match = re.search(r"https?://[^\s\)>]+", value)
    return match.group(0) if match else (value if value.startswith("http") else None)


def parse_track(value: str) -> str:
    """Determine a track ID from the Track section value."""
    value_stripped = value.strip()
    for body_key, track_id in TRACK_BODY_MAP.items():
        if body_key in value_stripped:
            return track_id
    # Fallback: also try label map keys
    for label_key, track_id in TRACK_LABEL_MAP.items():
        if label_key in value_stripped:
            return track_id
    return "unknown"


def parse_list(value: str) -> list[str]:
    """Parse a comma-separated or newline-separated list."""
    items: list[str] = []
    for line in value.splitlines():
        line = line.strip().lstrip("-").lstrip("*").strip()
        if not line or line == "_No response_":
            continue
        # Also expand comma-separated values
        for part in line.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items


def parse_checklist(value: str) -> dict[str, bool]:
    """Parse a checklist (``- [x]`` / ``- [ ]``)."""
    result: dict[str, bool] = {}
    for line in value.splitlines():
        match = re.match(r"^\s*-\s*\[([ xX])\]\s*(.+)$", line)
        if match:
            checked = match.group(1).lower() == "x"
            label = match.group(2).strip()
            result[label] = checked
    return result


def parse_demo(value: str) -> tuple[bool, str]:
    """Return (has_demo, description) from the Demo section."""
    stripped = value.strip()
    if not stripped or stripped == "_No response_":
        return False, ""
    # If URLs or image links are present, has_demo=True
    has_url = bool(re.search(r"https?://[^\s]+", stripped))
    has_image = bool(re.search(r"!\[.*?\]\(.*?\)", stripped))
    has_demo = has_url or has_image
    return has_demo, stripped


# ---------------------------------------------------------------------------
# Track detection
# ---------------------------------------------------------------------------
def _detect_track_from_labels(labels: list) -> str | None:
    """Return the track ID from labels. Returns None if not found."""
    for label in labels:
        # String if already filtered by jq, dict if raw
        name = label if isinstance(label, str) else label.get("name", "")
        if name in TRACK_LABEL_MAP:
            return TRACK_LABEL_MAP[name]
    return None


def _detect_track_from_body(body: str) -> str:
    """Return the track ID from the Issue body's Track section."""
    sections = _parse_sections(body)
    track_value = sections.get("Track", "")
    return parse_track(track_value)


def _detect_track(issue: dict[str, Any]) -> str:
    """Return the track ID with label priority, falling back to body detection."""
    labels = issue.get("labels", [])
    track = _detect_track_from_labels(labels)
    if track:
        return track
    body = issue.get("body") or ""
    return _detect_track_from_body(body)


# ---------------------------------------------------------------------------
# README fetching
# ---------------------------------------------------------------------------
async def _fetch_readme(repo_url: str | None) -> str | None:
    """Fetch the README from a GitHub repository. Returns None on failure."""
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
        # Trim to a maximum of 10,000 characters
        if len(content) > 10_000:
            content = content[:10_000] + "\n\n... (trimmed to 10,000 characters)"
        return content
    except Exception:
        logger.warning("Failed to fetch README: %s/%s", owner, repo, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Project name extraction helper
# ---------------------------------------------------------------------------
def _extract_project_name(issue: dict[str, Any]) -> str:
    """Extract the Project Name from Issue body. Falls back to Issue title."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    name = sections.get("Project Name", "").strip()
    if name and name != "_No response_":
        return name
    return issue.get("title", "")


# ---------------------------------------------------------------------------
# has_demo detection helper
# ---------------------------------------------------------------------------
def _extract_has_demo(issue: dict[str, Any]) -> bool:
    """Determine has_demo from the Demo section of the Issue body."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    demo_value = sections.get("Demo Video or Screenshots", "")
    has_demo, _ = parse_demo(demo_value)
    return has_demo


# ---------------------------------------------------------------------------
# repo_url extraction helper
# ---------------------------------------------------------------------------
def _extract_repo_url(issue: dict[str, Any]) -> str | None:
    """Extract the Repository URL from the Issue body."""
    body = issue.get("body") or ""
    sections = _parse_sections(body)
    url_value = sections.get("Repository URL", "")
    return parse_url(url_value)


# ---------------------------------------------------------------------------
# Tool: list_submissions
# ---------------------------------------------------------------------------
@mcp.tool()
async def list_submissions(
    track: str | None = None,
    state: str = "all",
) -> list[dict]:
    """Fetch the list of Agents League submissions.

    Args:
        track: Track name to filter by.
            ``"creative-apps"`` | ``"reasoning-agents"`` | ``"enterprise-agents"`` | None (all)
        state: Issue state. ``"open"`` | ``"closed"`` | ``"all"``

    Returns:
        A list of submission summaries. Each element is a dictionary
        containing issue_number, title, track, project_name, repo_url,
        created_at, has_demo.

    Raises:
        RuntimeError: When gh command execution fails.
    """
    # jq filter: extract only required fields
    jq_filter = (
        "[.[] | {number, title, body, labels: [.labels[].name], created_at}]"
    )

    args = [
        "api", f"repos/{REPO}/issues",
        "--method", "GET",
        "--paginate",
        "-q", jq_filter,
    ]

    # state parameter
    if state in ("open", "closed"):
        args.extend(["-f", f"state={state}"])
    else:
        args.extend(["-f", "state=all"])

    # Maximize per_page
    args.extend(["-F", "per_page=100"])

    raw = await _run_gh(*args)

    # --paginate may return multiple JSON arrays, so concatenate them
    all_issues: list[dict[str, Any]] = []
    for chunk in _split_json_arrays(raw):
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, list):
                all_issues.extend(parsed)
            else:
                all_issues.append(parsed)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse failed (skipping): %s", exc)

    results: list[dict[str, Any]] = []
    for issue in all_issues:
        issue_number = issue.get("number", 0)
        if issue_number < MIN_ISSUE_NUMBER:
            continue

        detected_track = _detect_track(issue)

        # Track filter
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
                "Failed to parse Issue #%d. Skipping.",
                issue_number,
                exc_info=True,
            )

    logger.info("list_submissions: fetched %d entries (track=%s, state=%s)", len(results), track, state)
    return results


# ---------------------------------------------------------------------------
# Tool: get_submission_detail
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_submission_detail(issue_number: int) -> dict:
    """Fetch detailed submission data for the specified Issue number.

    Parses each section of the Issue template and returns scoring data.
    GitHub Username is hidden during scoring to eliminate bias, but
    retained as the github_username field for report output.
    If repo_url points to a GitHub repository, the README is also fetched.

    Args:
        issue_number: The Issue number to fetch.

    Returns:
        A dictionary containing detailed submission information.

    Raises:
        RuntimeError: When gh command execution fails.
    """
    raw = await _run_gh(
        "api", f"repos/{REPO}/issues/{issue_number}",
    )
    issue: dict[str, Any] = json.loads(raw)

    body = issue.get("body") or ""
    sections = _parse_sections(body)

    # Detect track
    track_id = _detect_track(issue)

    # Parse each section
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

    # Fetch README
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
# Utilities
# ---------------------------------------------------------------------------
def _split_json_arrays(raw: str) -> list[str]:
    """Split concatenated JSON arrays returned by ``--paginate``.

    gh's ``--paginate`` may return multiple JSON arrays separated by newlines,
    so we track bracket depth to split them into individual arrays.
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

    # If no JSON arrays found, return the entire raw string
    if not chunks and raw.strip():
        chunks.append(raw.strip())

    return chunks
