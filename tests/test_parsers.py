"""Unit tests for the submission parser functions (no network calls)."""

from __future__ import annotations

import pytest

from saiten_mcp.tools.submissions import (
    _parse_sections,
    parse_text,
    parse_url,
    parse_track,
    parse_list,
    parse_checklist,
    parse_demo,
    _detect_track_from_labels,
    _detect_track_from_body,
)


# ---------------------------------------------------------------------------
# _parse_sections
# ---------------------------------------------------------------------------
class TestParseSections:
    """Tests for the Issue body section parser."""

    def test_basic_sections(self):
        body = """### Track

Creative Apps - GitHub Copilot

### Project Name

MyProject

### Description

Some description here."""
        sections = _parse_sections(body)
        assert "Track" in sections
        assert "Project Name" in sections
        assert "Description" in sections
        assert sections["Project Name"] == "MyProject"

    def test_empty_body(self):
        sections = _parse_sections("")
        assert sections == {}

    def test_no_headers(self):
        sections = _parse_sections("Just some text\nwithout headers")
        assert sections == {}

    def test_multiline_content(self):
        body = """### Description

Line one.
Line two.
Line three.

### Next Section

Next content."""
        sections = _parse_sections(body)
        assert "Line two." in sections["Description"]
        assert sections["Next Section"] == "Next content."

    def test_section_with_markdown(self):
        body = """### Demo

![screenshot](https://example.com/img.png)

Some **bold** text."""
        sections = _parse_sections(body)
        assert "![screenshot]" in sections["Demo"]


# ---------------------------------------------------------------------------
# parse_text
# ---------------------------------------------------------------------------
class TestParseText:
    """Tests for text parsing."""

    def test_basic(self):
        assert parse_text("  hello  ") == "hello"

    def test_empty(self):
        assert parse_text("") == ""

    def test_multiline(self):
        assert parse_text("\n text \n") == "text"


# ---------------------------------------------------------------------------
# parse_url
# ---------------------------------------------------------------------------
class TestParseUrl:
    """Tests for URL extraction."""

    def test_basic_url(self):
        assert parse_url("https://github.com/user/repo") == "https://github.com/user/repo"

    def test_url_in_text(self):
        result = parse_url("Repo: https://github.com/user/repo here")
        assert result == "https://github.com/user/repo"

    def test_http_url(self):
        result = parse_url("http://example.com")
        assert result == "http://example.com"

    def test_no_url(self):
        result = parse_url("no url here")
        assert result is None

    def test_empty(self):
        assert parse_url("") is None

    def test_url_with_parentheses(self):
        result = parse_url("[link](https://github.com/user/repo)")
        assert result is not None
        assert "github.com" in result


# ---------------------------------------------------------------------------
# parse_track
# ---------------------------------------------------------------------------
class TestParseTrack:
    """Tests for track detection from body text."""

    def test_creative_apps(self):
        assert parse_track("Creative Apps - GitHub Copilot") == "creative-apps"

    def test_reasoning_agents(self):
        assert parse_track("Reasoning Agents - Microsoft Foundry") == "reasoning-agents"

    def test_enterprise_agents(self):
        assert parse_track("Enterprise Agents - M365 Agents Toolkit") == "enterprise-agents"

    def test_unknown_track(self):
        assert parse_track("Some Unknown Track") == "unknown"

    def test_label_format(self):
        assert parse_track("🎨 Creative Apps") == "creative-apps"


# ---------------------------------------------------------------------------
# parse_list
# ---------------------------------------------------------------------------
class TestParseList:
    """Tests for list parsing."""

    def test_comma_separated(self):
        result = parse_list("Python, FastMCP, Pydantic")
        assert result == ["Python", "FastMCP", "Pydantic"]

    def test_newline_separated(self):
        result = parse_list("Python\nFastMCP\nPydantic")
        assert result == ["Python", "FastMCP", "Pydantic"]

    def test_dash_prefix(self):
        result = parse_list("- Python\n- FastMCP")
        assert result == ["Python", "FastMCP"]

    def test_no_response(self):
        result = parse_list("_No response_")
        assert result == []

    def test_empty(self):
        result = parse_list("")
        assert result == []

    def test_mixed_separators(self):
        result = parse_list("Python, FastMCP\nPydantic, YAML")
        assert len(result) == 4


# ---------------------------------------------------------------------------
# parse_checklist
# ---------------------------------------------------------------------------
class TestParseChecklist:
    """Tests for submission checklist parsing."""

    def test_checked_items(self):
        value = "- [x] Item one\n- [x] Item two"
        result = parse_checklist(value)
        assert result["Item one"] is True
        assert result["Item two"] is True

    def test_unchecked_items(self):
        value = "- [ ] Not done\n- [x] Done"
        result = parse_checklist(value)
        assert result["Not done"] is False
        assert result["Done"] is True

    def test_empty(self):
        assert parse_checklist("") == {}

    def test_mixed_case_x(self):
        value = "- [X] Capital X"
        result = parse_checklist(value)
        assert result["Capital X"] is True

    def test_no_checklist_items(self):
        value = "Just some text without checkboxes"
        assert parse_checklist(value) == {}


# ---------------------------------------------------------------------------
# parse_demo
# ---------------------------------------------------------------------------
class TestParseDemo:
    """Tests for demo detection."""

    def test_with_image(self):
        has_demo, desc = parse_demo("![demo](https://example.com/img.png)")
        assert has_demo is True
        assert "example.com" in desc

    def test_with_url(self):
        has_demo, desc = parse_demo("https://youtube.com/watch?v=123")
        assert has_demo is True

    def test_no_response(self):
        has_demo, desc = parse_demo("_No response_")
        assert has_demo is False
        assert desc == ""

    def test_empty(self):
        has_demo, desc = parse_demo("")
        assert has_demo is False

    def test_text_only(self):
        has_demo, desc = parse_demo("I will upload later")
        assert has_demo is False


# ---------------------------------------------------------------------------
# Track detection from labels
# ---------------------------------------------------------------------------
class TestDetectTrackFromLabels:
    """Tests for label-based track detection."""

    def test_string_label(self):
        labels = ["🎨 Creative Apps"]
        assert _detect_track_from_labels(labels) == "creative-apps"

    def test_dict_label(self):
        labels = [{"name": "🧠 Reasoning Agents"}]
        assert _detect_track_from_labels(labels) == "reasoning-agents"

    def test_enterprise_label(self):
        labels = [{"name": "💼 Enterprise Agents"}]
        assert _detect_track_from_labels(labels) == "enterprise-agents"

    def test_no_matching_label(self):
        labels = [{"name": "bug"}, {"name": "enhancement"}]
        assert _detect_track_from_labels(labels) is None

    def test_empty_labels(self):
        assert _detect_track_from_labels([]) is None

    def test_detect_from_body(self):
        body = "### Track\n\nCreative Apps - GitHub Copilot\n\n### Other\n\nStuff"
        assert _detect_track_from_body(body) == "creative-apps"
