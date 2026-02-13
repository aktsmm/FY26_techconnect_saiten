"""Unit tests for the scores tool (save/load logic, no network calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from typing import Any

import pytest

from saiten_mcp.tools.scores import save_scores


# ---------------------------------------------------------------------------
# save_scores unit tests
# ---------------------------------------------------------------------------
class TestSaveScores:
    """Tests for save_scores tool logic."""

    @pytest.mark.asyncio
    async def test_save_new_score(self, tmp_path: Path):
        """Saving a new score should create the file and increment count."""
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        new_score = {
            "issue_number": 200,
            "project_name": "NewProject",
            "track": "creative-apps",
            "criteria_scores": {"A": 7},
            "weighted_total": 70.0,
            "evidence": {"A": "MCP server found"},
            "confidence": "high",
            "red_flags_detected": [],
            "bonus_signals_detected": [],
            "strengths": ["Good MCP integration"],
            "improvements": ["No tests"],
            "summary": "A new project.",
        }

        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            result = await save_scores([new_score])

        assert result["saved_count"] == 1
        assert result["updated_count"] == 0
        assert result["total_in_store"] == 1

        # Verify file contents
        data = json.loads(scores_file.read_text(encoding="utf-8"))
        assert len(data["scores"]) == 1
        assert data["scores"][0]["issue_number"] == 200

    @pytest.mark.asyncio
    async def test_save_idempotent_overwrite(self, tmp_scores_file: Path):
        """Saving a score for an existing Issue should overwrite (idempotent)."""
        updated_score = {
            "issue_number": 100,  # exists in tmp_scores_file
            "project_name": "AlphaProject",
            "track": "creative-apps",
            "criteria_scores": {"A": 9},
            "weighted_total": 90.0,
            "evidence": {"A": "Updated evidence"},
            "confidence": "high",
            "red_flags_detected": [],
            "bonus_signals_detected": [],
            "strengths": ["Updated"],
            "improvements": ["Still needs work"],
            "summary": "Updated summary.",
        }

        with patch("saiten_mcp.tools.scores.SCORES_FILE", tmp_scores_file):
            result = await save_scores([updated_score])

        assert result["updated_count"] == 1
        assert result["saved_count"] == 0
        assert result["total_in_store"] == 2  # was 2, still 2

        data = json.loads(tmp_scores_file.read_text(encoding="utf-8"))
        alpha = next(s for s in data["scores"] if s["issue_number"] == 100)
        assert alpha["weighted_total"] == 90.0
        assert alpha["evidence"]["A"] == "Updated evidence"

    @pytest.mark.asyncio
    async def test_scores_sorted_descending(self, tmp_path: Path):
        """Scores should be sorted by weighted_total descending."""
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        scores = [
            {
                "issue_number": i,
                "project_name": f"Project{i}",
                "track": "creative-apps",
                "criteria_scores": {"A": i},
                "weighted_total": float(i * 10),
                "strengths": ["s"],
                "improvements": ["i"],
                "summary": "s",
            }
            for i in [3, 1, 5, 2, 4]
        ]

        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            await save_scores(scores)

        data = json.loads(scores_file.read_text(encoding="utf-8"))
        totals = [s["weighted_total"] for s in data["scores"]]
        assert totals == sorted(totals, reverse=True)

    @pytest.mark.asyncio
    async def test_metadata_updated(self, tmp_path: Path):
        """Metadata should have correct scored_count and last_updated."""
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        scores = [
            {
                "issue_number": 1,
                "project_name": "P",
                "track": "creative-apps",
                "criteria_scores": {"A": 5},
                "weighted_total": 50.0,
                "strengths": [],
                "improvements": [],
                "summary": "s",
            }
        ]

        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            await save_scores(scores)

        data = json.loads(scores_file.read_text(encoding="utf-8"))
        assert data["metadata"]["scored_count"] == 1
        assert "last_updated" in data["metadata"]

    @pytest.mark.asyncio
    async def test_empty_scores_list(self, tmp_path: Path):
        """Saving an empty list should not crash."""
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            result = await save_scores([])

        assert result["saved_count"] == 0
        assert result["total_in_store"] == 0


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------
class TestSaveScoresValidation:
    """Tests for input validation in save_scores."""

    @pytest.mark.asyncio
    async def test_rejects_missing_issue_number(self, tmp_path: Path):
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        bad_score = {
            "project_name": "Bad",
            "track": "creative-apps",
            "criteria_scores": {"A": 5},
            "weighted_total": 50.0,
            "strengths": [],
            "improvements": [],
            "summary": "",
        }
        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            with pytest.raises(ValueError, match="issue_number"):
                await save_scores([bad_score])

    @pytest.mark.asyncio
    async def test_rejects_invalid_weighted_total(self, tmp_path: Path):
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        bad_score = {
            "issue_number": 1,
            "project_name": "Bad",
            "track": "creative-apps",
            "criteria_scores": {"A": 5},
            "weighted_total": 150.0,
            "strengths": [],
            "improvements": [],
            "summary": "",
        }
        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            with pytest.raises(ValueError, match="weighted_total"):
                await save_scores([bad_score])

    @pytest.mark.asyncio
    async def test_rejects_criteria_score_out_of_range(self, tmp_path: Path):
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        bad_score = {
            "issue_number": 1,
            "project_name": "Bad",
            "track": "creative-apps",
            "criteria_scores": {"A": 15},
            "weighted_total": 50.0,
            "strengths": [],
            "improvements": [],
            "summary": "",
        }
        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            with pytest.raises(ValueError, match="must be 1-10"):
                await save_scores([bad_score])

    @pytest.mark.asyncio
    async def test_rejects_missing_track(self, tmp_path: Path):
        scores_file = tmp_path / "data" / "scores.json"
        scores_file.parent.mkdir(parents=True, exist_ok=True)

        bad_score = {
            "issue_number": 1,
            "project_name": "Bad",
            "track": "",
            "criteria_scores": {"A": 5},
            "weighted_total": 50.0,
            "strengths": [],
            "improvements": [],
            "summary": "",
        }
        with patch("saiten_mcp.tools.scores.SCORES_FILE", scores_file):
            with pytest.raises(ValueError, match="track"):
                await save_scores([bad_score])
