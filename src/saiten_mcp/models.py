"""Saiten MCP — Data Models (Pydantic)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Rubric models
# ---------------------------------------------------------------------------

class ScoringCriteria(BaseModel):
    """A single scoring criterion."""

    name: str
    weight: float = Field(ge=0.0, le=1.0)
    description: str
    scoring_guide: dict[str, str]


class Rubric(BaseModel):
    """Track-specific scoring rubric."""

    track: str
    track_display_name: str
    criteria: list[ScoringCriteria]
    notes: str = ""


# ---------------------------------------------------------------------------
# Submission models
# ---------------------------------------------------------------------------

class Submission(BaseModel):
    """Submission summary for Issue listing."""

    issue_number: int
    title: str
    track: str
    project_name: str
    repo_url: str | None = None
    created_at: str
    has_demo: bool = False


class SubmissionDetail(BaseModel):
    """Detailed submission info (scoring target)."""

    issue_number: int
    title: str
    track: str
    project_name: str
    description: str
    repo_url: str | None = None
    readme_content: str | None = None
    technologies: list[str] = Field(default_factory=list)
    technical_highlights: str = ""
    has_demo: bool = False
    demo_description: str = ""
    submission_checklist: dict[str, Any] = Field(default_factory=dict)
    team_members: str | None = None
    setup_summary: str = ""


# ---------------------------------------------------------------------------
# Score models
# ---------------------------------------------------------------------------

class CriteriaScore(BaseModel):
    """Score for an individual criterion."""

    name: str
    score: int = Field(ge=1, le=10)
    weight: float = Field(ge=0.0, le=1.0)


class SubmissionScore(BaseModel):
    """Scoring result for a single submission."""

    issue_number: int
    project_name: str
    track: str
    criteria_scores: dict[str, int]
    weighted_total: float = Field(ge=0.0, le=100.0)
    strengths: list[str]
    improvements: list[str]
    summary: str
    scored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoreMetadata(BaseModel):
    """Metadata for scores.json."""

    last_updated: str
    version: str = "1.0"
    total_submissions: int = 0
    scored_count: int = 0


class ScoreStore(BaseModel):
    """Top-level scores.json structure."""

    metadata: ScoreMetadata
    scores: list[SubmissionScore] = Field(default_factory=list)
