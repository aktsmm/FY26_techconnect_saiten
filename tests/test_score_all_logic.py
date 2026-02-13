"""Regression tests for scripts/score_all.py helper logic."""

from __future__ import annotations

import asyncio
import importlib.util
import uuid
from pathlib import Path


def _load_score_all_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "score_all.py"
    module_name = f"score_all_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_does_not_execute_main(monkeypatch):
    """Importing score_all should not execute main()."""
    called = {"value": False}

    def fake_run(*args, **kwargs):
        called["value"] = True
        return None

    monkeypatch.setattr(asyncio, "run", fake_run)
    _load_score_all_module()

    assert called["value"] is False


def test_creative_ux_recognizes_gif_and_setup_summary():
    """GIF demos and setup_summary should contribute to UX scoring."""
    score_all = _load_score_all_module()

    submission = {
        "issue_number": 9999,
        "project_name": "Demo Project",
        "track": "creative-apps",
        "issue_url": "https://example.com/issue/9999",
        "github_username": "demo-user",
        "repo_url": "https://github.com/demo/project",
        "description": "Detailed project description. " * 20,
        "technical_highlights": "Technical highlights with architecture and reliability. " * 5,
        "readme_content": "\n".join(
            [
                "# Demo Project",
                "## Overview",
                "## Architecture",
                "## Features",
                "## Workflow",
                "## Validation",
                "## Security",
                "## Testing",
            ]
        ),
        "demo_description": "![Demo](https://example.com/run.gif)",
        "has_demo": True,
        "setup_summary": "git clone https://github.com/demo/project && pip install -e .",
        "submission_checklist": {
            "My project meets the track-specific challenge requirements": True,
            "My repository includes a README.md with setup instructions": True,
            "My code does not contain hardcoded API keys or secrets": True,
            "I have included demo materials (video or screenshots)": True,
            "My project is my own work created during this hackathon": True,
        },
        "technologies": ["Python", "FastMCP", "GitHub Copilot", "pytest"],
    }

    repo_tree = {
        "total_source_files": 12,
        "total_test_files": 6,
        "total_files": 30,
        "commit_count": 8,
        "has_tests_dir": True,
        "has_ci": True,
        "has_gitignore": True,
        "has_env_example": True,
        "has_dockerfile": False,
        "languages": {".py": 12, ".md": 1},
    }

    result = score_all.score_creative_apps(submission, rubric={}, repo_tree=repo_tree)
    ux_evidence = result["evidence"]["UX & Presentation"]

    assert result["criteria_scores"]["UX & Presentation"] == 9
    assert "Animated GIF demo provided" in ux_evidence
    assert "Setup instructions provided via setup summary" in ux_evidence
    assert "No demo materials provided" not in ux_evidence
    assert "No clear setup instructions in README" not in ux_evidence
