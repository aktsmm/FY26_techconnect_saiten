"""Unit tests for the reports tool (no network calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from saiten_mcp.tools.reports import generate_ranking_report, _build_ranking_md


# ---------------------------------------------------------------------------
# _build_ranking_md
# ---------------------------------------------------------------------------
class TestBuildRankingMd:
    """Tests for the Markdown report builder."""

    def test_empty_scores(self):
        md = _build_ranking_md([], {}, top_n=5)
        assert "Agents League" in md
        assert "Top 5" in md

    def test_top_n_entries(self, sample_scores):
        md = _build_ranking_md(sample_scores, {"scored_count": 2}, top_n=2)
        assert "AlphaProject" in md
        assert "BetaProject" in md

    def test_track_sections_present(self, sample_scores):
        md = _build_ranking_md(sample_scores, {}, top_n=5)
        assert "Creative Apps" in md
        assert "Reasoning Agents" in md

    def test_individual_summaries(self, sample_scores):
        md = _build_ranking_md(sample_scores, {}, top_n=5)
        assert "Individual Evaluation Summaries" in md
        assert "67.8" in md  # AlphaProject score

    def test_report_contains_evidence_fields(self, sample_scores):
        """Scores with evidence should include strengths/improvements."""
        md = _build_ranking_md(sample_scores, {}, top_n=5)
        assert "MCP server with 3 tools" in md
        assert "No tests" in md


# ---------------------------------------------------------------------------
# generate_ranking_report
# ---------------------------------------------------------------------------
class TestGenerateRankingReport:
    """Tests for the generate_ranking_report MCP tool."""

    @pytest.mark.asyncio
    async def test_generates_report(self, tmp_scores_file: Path, tmp_path: Path):
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        with (
            patch("saiten_mcp.tools.reports.SCORES_FILE", tmp_scores_file),
            patch("saiten_mcp.tools.reports.REPORTS_DIR", report_dir),
        ):
            result = await generate_ranking_report(top_n=5)

        assert result["total_scored"] == 2
        assert len(result["top_entries"]) == 2

        report_path = report_dir / "ranking.md"
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")
        assert "Agents League" in content
        assert "BetaProject" in content

    @pytest.mark.asyncio
    async def test_empty_scores(self, tmp_path: Path):
        """Report generation with no scores should not crash."""
        scores_file = tmp_path / "scores.json"
        scores_file.write_text('{"metadata": {}, "scores": []}', encoding="utf-8")
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        with (
            patch("saiten_mcp.tools.reports.SCORES_FILE", scores_file),
            patch("saiten_mcp.tools.reports.REPORTS_DIR", report_dir),
        ):
            result = await generate_ranking_report(top_n=5)

        assert result["total_scored"] == 0
        assert result["top_entries"] == []

    @pytest.mark.asyncio
    async def test_missing_scores_file(self, tmp_path: Path):
        """Missing scores.json should generate an empty report."""
        scores_file = tmp_path / "nonexistent.json"
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        with (
            patch("saiten_mcp.tools.reports.SCORES_FILE", scores_file),
            patch("saiten_mcp.tools.reports.REPORTS_DIR", report_dir),
        ):
            result = await generate_ranking_report(top_n=5)

        assert result["total_scored"] == 0
