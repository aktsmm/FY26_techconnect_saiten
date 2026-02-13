"""Unit tests for the rubrics tool (no network calls)."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from saiten_mcp.tools.rubrics import get_scoring_rubric


@pytest.fixture
def rubric_files(rubrics_dir: Path) -> list[str]:
    """Return list of available rubric YAML files."""
    return [f.stem for f in rubrics_dir.glob("*.yaml")]


# ---------------------------------------------------------------------------
# Rubric file integrity
# ---------------------------------------------------------------------------
class TestRubricFiles:
    """Validate the rubric YAML files are well-formed."""

    @pytest.mark.parametrize("track", [
        "creative-apps",
        "reasoning-agents",
        "enterprise-agents",
    ])
    def test_rubric_file_exists(self, rubrics_dir: Path, track: str):
        path = rubrics_dir / f"{track}.yaml"
        assert path.exists(), f"Rubric file missing: {path}"

    @pytest.mark.parametrize("track", [
        "creative-apps",
        "reasoning-agents",
        "enterprise-agents",
    ])
    def test_rubric_valid_yaml(self, rubrics_dir: Path, track: str):
        path = rubrics_dir / f"{track}.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "track" in data
        assert "criteria" in data

    @pytest.mark.parametrize("track", [
        "creative-apps",
        "reasoning-agents",
        "enterprise-agents",
    ])
    def test_rubric_has_scoring_policy(self, rubrics_dir: Path, track: str):
        """Verify the enhanced scoring_policy exists in each rubric."""
        path = rubrics_dir / f"{track}.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        policy = data.get("scoring_policy")
        assert policy is not None, f"{track}: scoring_policy missing"
        assert policy.get("evidence_required") is True
        assert isinstance(policy.get("red_flags"), list)
        assert isinstance(policy.get("bonus_signals"), list)
        assert isinstance(policy.get("differentiation_rules"), list)

    @pytest.mark.parametrize("track", [
        "creative-apps",
        "reasoning-agents",
        "enterprise-agents",
    ])
    def test_rubric_criteria_have_evidence_signals(self, rubrics_dir: Path, track: str):
        """Verify each criterion has evidence_signals with positive and negative."""
        path = rubrics_dir / f"{track}.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for criterion in data["criteria"]:
            name = criterion["name"]
            signals = criterion.get("evidence_signals")
            assert signals is not None, f"{track}/{name}: evidence_signals missing"
            assert isinstance(signals.get("positive"), list), f"{track}/{name}: positive signals missing"
            assert isinstance(signals.get("negative"), list), f"{track}/{name}: negative signals missing"
            assert len(signals["positive"]) > 0, f"{track}/{name}: no positive signals"
            assert len(signals["negative"]) > 0, f"{track}/{name}: no negative signals"

    @pytest.mark.parametrize("track", [
        "creative-apps",
        "reasoning-agents",
        "enterprise-agents",
    ])
    def test_rubric_weights_sum_to_one(self, rubrics_dir: Path, track: str):
        """Verify criterion weights sum to approximately 1.0."""
        path = rubrics_dir / f"{track}.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        total_weight = sum(c["weight"] for c in data["criteria"])
        assert abs(total_weight - 1.0) < 0.01, (
            f"{track}: weights sum to {total_weight}, expected ~1.0"
        )


# ---------------------------------------------------------------------------
# get_scoring_rubric tool
# ---------------------------------------------------------------------------
class TestGetScoringRubric:
    """Tests for the get_scoring_rubric MCP tool."""

    @pytest.mark.asyncio
    async def test_creative_apps_rubric(self):
        rubric = await get_scoring_rubric("creative-apps")
        assert rubric["track"] == "creative-apps"
        assert len(rubric["criteria"]) == 5
        assert abs(rubric["total_weight"] - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_reasoning_agents_rubric(self):
        rubric = await get_scoring_rubric("reasoning-agents")
        assert rubric["track"] == "reasoning-agents"
        assert len(rubric["criteria"]) == 5

    @pytest.mark.asyncio
    async def test_enterprise_agents_rubric(self):
        rubric = await get_scoring_rubric("enterprise-agents")
        assert rubric["track"] == "enterprise-agents"
        assert len(rubric["criteria"]) == 3

    @pytest.mark.asyncio
    async def test_invalid_track_raises(self):
        with pytest.raises(ValueError):
            await get_scoring_rubric("nonexistent-track")

    @pytest.mark.asyncio
    async def test_rubric_includes_scoring_guide(self):
        rubric = await get_scoring_rubric("creative-apps")
        for criterion in rubric["criteria"]:
            assert "scoring_guide" in criterion
            guide = criterion["scoring_guide"]
            assert isinstance(guide, dict)
            assert len(guide) > 0
