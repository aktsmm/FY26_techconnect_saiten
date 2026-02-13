"""Unit tests for the data models (Pydantic)."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from saiten_mcp.models import (
    CriteriaScore,
    Rubric,
    ScoringCriteria,
    Submission,
    SubmissionDetail,
    SubmissionScore,
    ScoreMetadata,
    ScoreStore,
)


# ---------------------------------------------------------------------------
# CriteriaScore
# ---------------------------------------------------------------------------
class TestCriteriaScore:
    """Tests for CriteriaScore validation."""

    def test_valid_score(self):
        cs = CriteriaScore(name="Accuracy", score=7, weight=0.25)
        assert cs.score == 7
        assert cs.weight == 0.25

    def test_score_min_boundary(self):
        cs = CriteriaScore(name="Accuracy", score=1, weight=0.0)
        assert cs.score == 1

    def test_score_max_boundary(self):
        cs = CriteriaScore(name="Accuracy", score=10, weight=1.0)
        assert cs.score == 10

    def test_score_below_min_rejected(self):
        with pytest.raises(Exception):
            CriteriaScore(name="Accuracy", score=0, weight=0.5)

    def test_score_above_max_rejected(self):
        with pytest.raises(Exception):
            CriteriaScore(name="Accuracy", score=11, weight=0.5)

    def test_weight_negative_rejected(self):
        with pytest.raises(Exception):
            CriteriaScore(name="Accuracy", score=5, weight=-0.1)


# ---------------------------------------------------------------------------
# SubmissionScore
# ---------------------------------------------------------------------------
class TestSubmissionScore:
    """Tests for SubmissionScore with evidence-anchored fields."""

    def test_basic_creation(self):
        s = SubmissionScore(
            issue_number=42,
            project_name="TestProject",
            track="creative-apps",
            criteria_scores={"Accuracy": 7, "Creativity": 8},
            weighted_total=75.0,
            strengths=["Good tests"],
            improvements=["Needs docs"],
            summary="Solid project.",
        )
        assert s.issue_number == 42
        assert s.weighted_total == 75.0

    def test_evidence_defaults_to_empty(self):
        s = SubmissionScore(
            issue_number=1,
            project_name="P",
            track="creative-apps",
            criteria_scores={"A": 5},
            weighted_total=50.0,
            strengths=[],
            improvements=[],
            summary="Test",
        )
        assert s.evidence == {}
        assert s.confidence == "medium"
        assert s.red_flags_detected == []
        assert s.bonus_signals_detected == []

    def test_evidence_populated(self):
        s = SubmissionScore(
            issue_number=1,
            project_name="P",
            track="creative-apps",
            criteria_scores={"A": 5},
            weighted_total=50.0,
            evidence={"A": "MCP server found in src/mcp.py"},
            confidence="high",
            red_flags_detected=["No README"],
            bonus_signals_detected=["MCP server found"],
            strengths=["Good"],
            improvements=["Bad"],
            summary="Test",
        )
        assert s.evidence["A"] == "MCP server found in src/mcp.py"
        assert s.confidence == "high"
        assert len(s.red_flags_detected) == 1

    def test_weighted_total_range_low(self):
        with pytest.raises(Exception):
            SubmissionScore(
                issue_number=1,
                project_name="P",
                track="t",
                criteria_scores={},
                weighted_total=-1.0,
                strengths=[],
                improvements=[],
                summary="",
            )

    def test_weighted_total_range_high(self):
        with pytest.raises(Exception):
            SubmissionScore(
                issue_number=1,
                project_name="P",
                track="t",
                criteria_scores={},
                weighted_total=101.0,
                strengths=[],
                improvements=[],
                summary="",
            )

    def test_scored_at_auto_populated(self):
        s = SubmissionScore(
            issue_number=1,
            project_name="P",
            track="t",
            criteria_scores={},
            weighted_total=0.0,
            strengths=[],
            improvements=[],
            summary="",
        )
        assert isinstance(s.scored_at, datetime)
        assert s.scored_at.tzinfo is not None


# ---------------------------------------------------------------------------
# ScoreStore
# ---------------------------------------------------------------------------
class TestScoreStore:
    """Tests for the top-level scores.json structure."""

    def test_empty_store(self):
        store = ScoreStore(
            metadata=ScoreMetadata(last_updated="2026-01-01T00:00:00Z"),
        )
        assert store.scores == []
        assert store.metadata.scored_count == 0

    def test_store_with_scores(self, sample_scores):
        scores = [
            SubmissionScore(**s)
            for s in sample_scores
        ]
        store = ScoreStore(
            metadata=ScoreMetadata(
                last_updated="2026-01-01T00:00:00Z",
                scored_count=len(scores),
            ),
            scores=scores,
        )
        assert len(store.scores) == 2
        assert store.metadata.scored_count == 2


# ---------------------------------------------------------------------------
# Submission & SubmissionDetail
# ---------------------------------------------------------------------------
class TestSubmission:
    """Tests for Submission model."""

    def test_basic_submission(self):
        s = Submission(
            issue_number=10,
            title="Test",
            track="creative-apps",
            project_name="TestProject",
            created_at="2026-01-01T00:00:00Z",
        )
        assert s.repo_url is None
        assert s.has_demo is False

    def test_submission_with_all_fields(self):
        s = Submission(
            issue_number=10,
            title="Test",
            track="creative-apps",
            project_name="TestProject",
            repo_url="https://github.com/user/repo",
            created_at="2026-01-01T00:00:00Z",
            has_demo=True,
        )
        assert s.repo_url == "https://github.com/user/repo"


class TestSubmissionDetail:
    """Tests for SubmissionDetail model."""

    def test_detail_defaults(self):
        d = SubmissionDetail(
            issue_number=10,
            title="Test",
            track="creative-apps",
            project_name="TestProject",
            description="A test project",
        )
        assert d.technologies == []
        assert d.readme_content is None
        assert d.has_demo is False
        assert d.submission_checklist == {}
