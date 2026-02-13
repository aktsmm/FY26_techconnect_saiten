"""Shared test fixtures for the saiten-mcp test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Return the data/ directory path."""
    return project_root / "data"


@pytest.fixture
def rubrics_dir(data_dir: Path) -> Path:
    """Return the data/rubrics/ directory path."""
    return data_dir / "rubrics"


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_issue_body() -> str:
    """Return a realistic Issue body matching the submission template."""
    return """### Track

Creative Apps - GitHub Copilot

### Project Name

TestProject

### Microsoft Alias

_No response_

### GitHub Username

testuser

### Repository URL

https://github.com/testuser/test-project

### Project Description

A test project for validating the scoring pipeline.

### Demo Video or Screenshots

![demo](https://example.com/demo.png)

### Primary Programming Language

Python

### Key Technologies Used

Python, FastMCP, Pydantic, GitHub Copilot

### Submission Requirements

- [x] My project meets the track-specific challenge requirements
- [x] My repository includes a README.md with setup instructions
- [x] My code does not contain hardcoded API keys or secrets
- [ ] I have included demo materials (video or screenshots)
- [x] My project is my own work created during this hackathon

### Technical Highlights

Built a multi-agent scoring system with MCP integration.

### Quick Setup Summary

pip install -e . && python -m saiten_mcp.server

### Team Members (if any)

_No response_
"""


@pytest.fixture
def sample_issue_raw() -> dict[str, Any]:
    """Return a raw Issue dict as returned by GitHub API."""
    return {
        "number": 99,
        "title": "TestProject Submission",
        "body": """### Track\n\nCreative Apps - GitHub Copilot\n\n### Project Name\n\nTestProject\n\n### Repository URL\n\nhttps://github.com/testuser/test-project\n\n### Project Description\n\nA test project.\n\n### Demo Video or Screenshots\n\n![demo](https://example.com/demo.png)\n\n### Key Technologies Used\n\nPython, FastMCP\n\n### Submission Requirements\n\n- [x] Required 1\n- [ ] Required 2\n\n### Technical Highlights\n\nMulti-agent system.\n\n### Quick Setup Summary\n\npip install .""",
        "labels": [{"name": "🎨 Creative Apps"}],
        "created_at": "2026-02-01T10:00:00Z",
    }


@pytest.fixture
def sample_scores() -> list[dict[str, Any]]:
    """Return sample scoring results for testing."""
    return [
        {
            "issue_number": 100,
            "project_name": "AlphaProject",
            "track": "creative-apps",
            "criteria_scores": {
                "Accuracy & Relevance": 7,
                "Reasoning & Multi-step Thinking": 6,
                "Creativity & Originality": 8,
                "UX & Presentation": 7,
                "Reliability & Safety": 6,
            },
            "evidence": {
                "Accuracy & Relevance": "MCP server with 3 tools implemented.",
                "Reasoning & Multi-step Thinking": "Linear flow with error handling.",
                "Creativity & Originality": "Novel combination of MCP + CLI.",
                "UX & Presentation": "README with architecture diagram.",
                "Reliability & Safety": "Try/catch in main handler, .env.example provided.",
            },
            "confidence": "high",
            "red_flags_detected": [],
            "bonus_signals_detected": ["MCP server implementation found in code"],
            "weighted_total": 67.8,
            "strengths": ["MCP server with 3 tools", "Clean architecture"],
            "improvements": ["No tests", "No rate limiting"],
            "summary": "A solid MCP-based scoring tool.",
        },
        {
            "issue_number": 101,
            "project_name": "BetaProject",
            "track": "reasoning-agents",
            "criteria_scores": {
                "Accuracy & Relevance": 8,
                "Reasoning & Multi-step Thinking": 9,
                "Creativity & Originality": 7,
                "User Experience & Presentation": 6,
                "Technical Implementation": 7,
            },
            "evidence": {
                "Accuracy & Relevance": "Foundry model deployed with grounding.",
                "Reasoning & Multi-step Thinking": "ReAct loop with self-correction.",
                "Creativity & Originality": "Novel content pipeline approach.",
                "User Experience & Presentation": "Screenshots only, no video.",
                "Technical Implementation": "Clean code, missing tests.",
            },
            "confidence": "medium",
            "red_flags_detected": [],
            "bonus_signals_detected": ["Self-reflection loop implemented"],
            "weighted_total": 75.5,
            "strengths": ["ReAct loop", "Grounding with vector store"],
            "improvements": ["No video demo", "Missing tests"],
            "summary": "Strong reasoning pipeline with self-correction.",
        },
    ]


@pytest.fixture
def sample_rubric_data() -> dict[str, Any]:
    """Return a minimal rubric data structure for testing."""
    return {
        "track": "creative-apps",
        "track_display_name": "🎨 Creative Apps",
        "notes": "Test rubric",
        "scoring_policy": {
            "evidence_required": True,
            "min_evidence_per_criterion": 1,
            "differentiation_rules": [
                "Score 8+ requires specific technical evidence",
            ],
            "red_flags": [
                {"signal": "No README", "max_ux_score": 4},
            ],
            "bonus_signals": [
                {"signal": "MCP server implementation", "bonus_criteria": "Accuracy & Relevance", "min_score": 7},
            ],
        },
        "criteria": [
            {
                "name": "Accuracy & Relevance",
                "weight": 0.5,
                "description": "Test criterion",
                "scoring_guide": {"1-3": "Bad", "4-6": "Mid", "7-9": "Good", "10": "Exceptional"},
                "evidence_signals": {
                    "positive": ["MCP server found"],
                    "negative": ["No MCP integration"],
                },
            },
            {
                "name": "Creativity & Originality",
                "weight": 0.5,
                "description": "Test criterion 2",
                "scoring_guide": {"1-3": "Bad", "4-6": "Mid", "7-9": "Good", "10": "Exceptional"},
                "evidence_signals": {
                    "positive": ["Novel approach"],
                    "negative": ["Tutorial clone"],
                },
            },
        ],
    }


@pytest.fixture
def tmp_scores_file(tmp_path: Path, sample_scores: list) -> Path:
    """Create a temporary scores.json file for testing."""
    scores_file = tmp_path / "scores.json"
    data = {
        "metadata": {
            "last_updated": "2026-02-13T00:00:00+00:00",
            "version": "1.0",
            "total_submissions": 2,
            "scored_count": 2,
        },
        "scores": sample_scores,
    }
    scores_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return scores_file
