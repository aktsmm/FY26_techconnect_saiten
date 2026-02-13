"""Baseline signal extraction and mechanical scoring.

Phase A of the two-phase scoring pipeline:
  Phase A (this script): Mechanical baseline — keyword matching,
    checklist ratios, README section counts, demo presence detection.
    Produces a STARTING POINT, not the final score.
  Phase B (saiten-scorer agent): AI qualitative review — the Copilot
    agent reads each submission, judges quality holistically, and
    adjusts scores via adjust_scores() with rationale.

Follows the saiten-scorer protocol:
- Phase 0: Deep Analysis
- Phase 1: Evidence-Anchored Scoring
- Phase 2: Quality Gate
"""

import asyncio
import io
import json
import re
import sys

# Ensure stdout handles Unicode on Windows (cp932 cannot encode some chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
from typing import Any

sys.path.insert(0, "src")
from saiten_mcp.tools.scores import save_scores
from saiten_mcp.tools.rubrics import get_scoring_rubric

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _has_keyword(text: str, keywords: list[str]) -> list[str]:
    """Return matched keywords found in text (case-insensitive)."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def _count_sections(readme: str) -> int:
    """Count markdown heading sections in README."""
    return len(re.findall(r"^#{1,4}\s+", readme, re.MULTILINE))


def _has_code_blocks(text: str) -> bool:
    return "`" in text


def _has_architecture_diagram(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in [
        "architecture", "flow diagram", "system design", "mermaid",
        "flowchart", "sequence diagram", "`mermaid",
    ])


def _has_setup_instructions(readme: str) -> bool:
    lower = readme.lower()
    return any(kw in lower for kw in [
        "installation", "getting started", "setup", "how to run",
        "prerequisites", "quick start", "npm install", "pip install",
        "docker", "go mod", "yarn", "dotnet",
    ])


def _has_tests(readme: str) -> bool:
    lower = readme.lower()
    return any(kw in lower for kw in [
        "test", "pytest", "jest", "unittest", "xunit", "nunit",
        "coverage", "ci/cd", "github actions",
    ])


def _has_error_handling(readme: str) -> bool:
    lower = readme.lower()
    return any(kw in lower for kw in [
        "error handling", "try/catch", "exception", "retry",
        "fallback", "graceful", "error recovery", "validation",
    ])


def _has_mcp(sub: dict) -> bool:
    text = _all_text(sub).lower()
    return "mcp" in text


def _has_security(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in [
        ".env", "environment variable", "secret", "api key management",
        "oauth", "authentication", "gitignore", "credential",
    ])


def _has_reasoning(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in [
        "chain-of-thought", "cot", "react", "reasoning",
        "multi-step", "self-reflection", "agent loop",
        "observe", "think", "act", "plan", "evaluate",
    ])


def _has_multi_agent(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in [
        "multi-agent", "multi agent", "orchestrat",
        "swarm", "connected agent", "autogen", "semantic kernel",
        "crew", "supervisor",
    ])


def _demo_quality(sub: dict) -> str:
    """Detect demo type: 'video', 'screenshots', 'url', 'gif', 'none'."""
    demo = (sub.get("demo_description") or "").lower()
    demo_url = (sub.get("demo_url") or "").lower()
    combined = demo + " " + demo_url

    # Check gif (common in hackathons)
    if ".gif" in combined:
        return "gif"
    if any(kw in combined for kw in ["video", "youtube", "loom", ".mp4", ".mov"]):
        return "video"
    if any(kw in combined for kw in ["deploy", "live", "hosted", "azurewebsites", "vercel", "netlify"]):
        return "url"
    if any(kw in combined for kw in ["screenshot", "img", "image", "<img", "png", "jpg"]):
        return "screenshots"
    if sub.get("has_demo"):
        return "screenshots"  # has_demo=True but unclassified
    return "none"


def _all_text(sub: dict) -> str:
    """Combine all textual fields for keyword search."""
    parts = [
        sub.get("description") or "",
        sub.get("technical_highlights") or "",
        sub.get("setup_summary") or "",
        sub.get("readme_content") or "",
        sub.get("demo_description") or "",
    ]
    techs = sub.get("technologies") or []
    parts.append(", ".join(techs))
    return "\n".join(parts)


def _checklist_ratio(sub: dict) -> float:
    """Calculate checklist completion ratio. Handles both dict and list formats."""
    cl = sub.get("submission_checklist")
    if isinstance(cl, dict) and cl:
        checked = sum(1 for v in cl.values() if v)
        return checked / len(cl)
    # Also check checklist_items (list of strings = all checked)
    cl_list = sub.get("checklist_items")
    if isinstance(cl_list, list) and cl_list:
        return 1.0  # list format means all items are checked
    return 0.0


# --------------------------------------------------------------------------
# Repository analysis signals
# --------------------------------------------------------------------------

def _apply_repo_signals(
    criteria_scores: dict[str, int],
    evidence: dict[str, str],
    repo_tree: dict | None,
    sub: dict,
) -> tuple[dict[str, int], dict[str, str], list[str], list[str]]:
    """Adjust scores based on actual repository content analysis.

    This is the key function that verifies claims made in Issue/README
    against the actual repository file structure.

    Returns (adjusted_criteria_scores, adjusted_evidence, red_flags, bonus_signals).
    """
    red_flags = []
    bonus_signals = []

    if repo_tree is None:
        # No repo data — penalize all criteria
        red_flags.append("Repository inaccessible or private")
        for crit in criteria_scores:
            criteria_scores[crit] = max(1, criteria_scores[crit] - 2)
            evidence[crit] = evidence.get(crit, "") + ". REPO NOT ACCESSIBLE — scores penalized"
        return criteria_scores, evidence, red_flags, bonus_signals

    src_count = repo_tree.get("total_source_files", 0)
    test_count = repo_tree.get("total_test_files", 0)
    total_files = repo_tree.get("total_files", 0)
    commit_count = repo_tree.get("commit_count", 0)
    has_tests_dir = repo_tree.get("has_tests_dir", False)
    has_ci = repo_tree.get("has_ci", False)
    has_gitignore = repo_tree.get("has_gitignore", False)
    has_env_example = repo_tree.get("has_env_example", False)
    has_dockerfile = repo_tree.get("has_dockerfile", False)
    languages = repo_tree.get("languages", {})

    # --- Empty/minimal repo detection ---
    if src_count == 0:
        red_flags.append(f"No source code files found in repo ({total_files} total files)")
        # Heavily penalize: claims not backed by code
        for crit in criteria_scores:
            criteria_scores[crit] = max(1, criteria_scores[crit] - 3)
            evidence[crit] = evidence.get(crit, "") + f". NO SOURCE CODE in repo ({total_files} files total)"
        return criteria_scores, evidence, red_flags, bonus_signals

    if src_count <= 3:
        red_flags.append(f"Minimal source code: only {src_count} source files")
        # Moderate penalty for very thin repos
        for crit in ["Accuracy & Relevance", "Creativity & Originality",
                     "Technical Implementation", "Reasoning & Multi-step Thinking"]:
            if crit in criteria_scores:
                criteria_scores[crit] = max(1, criteria_scores[crit] - 1)
                evidence[crit] = evidence.get(crit, "") + f". Minimal source: {src_count} files"

    # --- Source code depth signals ---
    repo_info = f"Repo: {src_count} source, {test_count} test, {total_files} total files, {commit_count} commits"

    # Reward substantial codebases
    if src_count >= 20:
        bonus_signals.append(f"Substantial codebase ({src_count} source files)")
        # Boost implementation-related criteria
        for crit in ["Accuracy & Relevance", "Technical Implementation"]:
            if crit in criteria_scores and criteria_scores[crit] < 10:
                criteria_scores[crit] = min(10, criteria_scores[crit] + 1)
                evidence[crit] = evidence.get(crit, "") + f". {repo_info}"
    elif src_count >= 10:
        for crit in ["Accuracy & Relevance", "Technical Implementation"]:
            if crit in criteria_scores:
                evidence[crit] = evidence.get(crit, "") + f". {repo_info}"
    elif src_count < 5:
        for crit in ["Accuracy & Relevance", "Technical Implementation"]:
            if crit in criteria_scores and criteria_scores[crit] > 7:
                criteria_scores[crit] = max(5, criteria_scores[crit] - 1)
                evidence[crit] = evidence.get(crit, "") + f". Limited code: {repo_info}"

    # --- Test verification ---
    # If README/description claims tests but no test files exist, penalize
    all_text = _all_text(sub).lower()
    claims_tests = _has_tests(all_text)
    if claims_tests and test_count == 0 and not has_tests_dir:
        red_flags.append("Claims testing but no test files found in repo")
        for crit in ["Reliability & Safety"]:
            if crit in criteria_scores:
                criteria_scores[crit] = max(1, criteria_scores[crit] - 2)
                evidence[crit] = evidence.get(crit, "") + ". Claims tests but 0 test files in repo"
    elif test_count >= 5:
        bonus_signals.append(f"Verified: {test_count} test files in repo")
        for crit in ["Reliability & Safety"]:
            if crit in criteria_scores and criteria_scores[crit] < 10:
                criteria_scores[crit] = min(10, criteria_scores[crit] + 1)
                evidence[crit] = evidence.get(crit, "") + f". Verified {test_count} test files"
    elif test_count > 0:
        for crit in ["Reliability & Safety"]:
            if crit in criteria_scores:
                evidence[crit] = evidence.get(crit, "") + f". {test_count} test files found"

    # --- CI/CD verification ---
    if has_ci:
        bonus_signals.append("CI/CD pipeline configured")
        for crit in ["Reliability & Safety"]:
            if crit in criteria_scores and criteria_scores[crit] < 10:
                criteria_scores[crit] = min(10, criteria_scores[crit] + 1)
                evidence[crit] = evidence.get(crit, "") + ". CI/CD pipeline found"

    # --- Security signals from actual files ---
    if has_gitignore:
        for crit in ["Reliability & Safety"]:
            if crit in criteria_scores:
                evidence[crit] = evidence.get(crit, "") + ". .gitignore present"
    if has_env_example:
        bonus_signals.append(".env.example provided for secure config")

    # --- Multi-language / complexity ---
    if len(languages) >= 3:
        bonus_signals.append(f"Multi-language project ({', '.join(languages.keys())})")
        for crit in ["Creativity & Originality", "Innovation & Creativity"]:
            if crit in criteria_scores:
                evidence[crit] = evidence.get(crit, "") + f". Multi-language: {', '.join(languages.keys())}"

    # --- Commit depth ---
    if commit_count >= 20:
        bonus_signals.append(f"Active development ({commit_count} commits)")
    elif commit_count <= 3:
        red_flags.append(f"Very few commits ({commit_count}) — may be template or rushed")
        for crit in ["Creativity & Originality", "Innovation & Creativity"]:
            if crit in criteria_scores and criteria_scores[crit] > 5:
                criteria_scores[crit] = max(3, criteria_scores[crit] - 1)
                evidence[crit] = evidence.get(crit, "") + f". Only {commit_count} commits"

    # --- Dockerfile bonus ---
    if has_dockerfile:
        bonus_signals.append("Containerized (Dockerfile found)")

    # Clamp all scores
    for crit in criteria_scores:
        criteria_scores[crit] = max(1, min(10, criteria_scores[crit]))

    return criteria_scores, evidence, red_flags, bonus_signals


# --------------------------------------------------------------------------
# Track-specific scorers
# --------------------------------------------------------------------------

def score_creative_apps(sub: dict, rubric: dict, repo_tree: dict | None = None) -> dict:
    readme = sub.get("readme_content") or ""
    all_text = _all_text(sub)
    desc = sub.get("description") or ""
    tech_highlights = sub.get("technical_highlights") or ""
    demo_type = _demo_quality(sub)
    has_readme = bool(readme)
    readme_sections = _count_sections(readme) if has_readme else 0
    checklist_r = _checklist_ratio(sub)
    techs = sub.get("technologies") or []

    # --- Accuracy & Relevance ---
    acc_score = 5
    acc_evidence_parts = []

    if _has_mcp(sub):
        acc_score += 2
        mcp_details = _has_keyword(all_text, ["mcp server", "mcp tool", "mcp integration", "mcp client"])
        acc_evidence_parts.append(f"MCP integration found: {', '.join(mcp_details) if mcp_details else 'MCP mentioned in project'}")

    copilot_kw = _has_keyword(all_text, ["copilot", "github copilot", "copilot sdk", "copilot chat"])
    if copilot_kw:
        acc_score += 1
        acc_evidence_parts.append(f"Copilot usage: {', '.join(set(copilot_kw))}")

    if checklist_r >= 0.8:
        acc_score += 1
        acc_evidence_parts.append(f"Checklist: {int(checklist_r*100)}% requirements met")
    elif checklist_r < 0.5:
        acc_score -= 1
        acc_evidence_parts.append(f"Only {int(checklist_r*100)}% of checklist items completed")

    if len(desc) > 200:
        acc_evidence_parts.append(f"Detailed description ({len(desc)} chars)")
    elif len(desc) < 50:
        acc_score -= 1
        acc_evidence_parts.append("Description is very brief")

    if not sub.get("repo_url"):
        acc_score -= 2
        acc_evidence_parts.append("No repository URL provided")

    acc_score = max(1, min(10, acc_score))
    acc_evidence = ". ".join(acc_evidence_parts) if acc_evidence_parts else "Basic submission with limited detail"

    # --- Reasoning & Multi-step Thinking ---
    reas_score = 5
    reas_evidence_parts = []

    if _has_reasoning(all_text):
        reas_score += 2
        reasoning_kw = _has_keyword(all_text, ["chain-of-thought", "cot", "react", "self-reflection", "agent loop", "multi-step"])
        reas_evidence_parts.append(f"Reasoning patterns: {', '.join(set(reasoning_kw))}")

    if _has_multi_agent(all_text):
        reas_score += 1
        agent_kw = _has_keyword(all_text, ["multi-agent", "orchestrat", "swarm", "autogen", "semantic kernel"])
        reas_evidence_parts.append(f"Multi-agent architecture: {', '.join(set(agent_kw))}")

    if _has_error_handling(all_text):
        reas_score += 1
        reas_evidence_parts.append("Error handling or recovery logic documented")

    if not _has_reasoning(all_text) and not _has_multi_agent(all_text):
        reas_score -= 1
        reas_evidence_parts.append("No explicit reasoning patterns or multi-step logic documented")

    reas_score = max(1, min(10, reas_score))
    reas_evidence = ". ".join(reas_evidence_parts) if reas_evidence_parts else "Limited reasoning chain documentation"

    # --- Creativity & Originality ---
    cre_score = 5
    cre_evidence_parts = []

    # Project name and description analysis for originality signals
    novelty_kw = _has_keyword(all_text, [
        "novel", "innovative", "unique", "first", "original",
        "custom", "new approach", "differentiator",
    ])
    if novelty_kw:
        cre_score += 1
        cre_evidence_parts.append(f"Novelty signals: {', '.join(set(novelty_kw))}")

    if len(techs) >= 4:
        cre_score += 1
        cre_evidence_parts.append(f"Diverse technology combination: {', '.join(techs[:5])}")

    if len(desc) > 300 and len(tech_highlights) > 50:
        cre_score += 1
        cre_evidence_parts.append("Detailed project description with technical highlights")

    template_kw = _has_keyword(desc, ["my hackathon project", "my awesome", "todo", "sample", "template"])
    if template_kw:
        cre_score -= 2
        cre_evidence_parts.append(f"Appears to be template/generic project: {', '.join(template_kw)}")

    cre_score = max(1, min(10, cre_score))
    cre_evidence = ". ".join(cre_evidence_parts) if cre_evidence_parts else "Standard project concept"

    # --- UX & Presentation ---
    ux_score = 5
    ux_evidence_parts = []

    if demo_type == "video":
        ux_score += 2
        ux_evidence_parts.append("Video demo provided")
    elif demo_type == "screenshots":
        ux_score += 1
        ux_evidence_parts.append("Screenshots provided in demo section")
    elif demo_type == "url":
        ux_score += 2
        ux_evidence_parts.append("Live demo URL available")
    else:
        ux_score -= 2
        ux_evidence_parts.append("No demo materials provided")

    if has_readme:
        if readme_sections >= 8:
            ux_score += 2
            ux_evidence_parts.append(f"Comprehensive README with {readme_sections} sections")
        elif readme_sections >= 4:
            ux_score += 1
            ux_evidence_parts.append(f"README with {readme_sections} sections")
        else:
            ux_evidence_parts.append(f"Brief README ({readme_sections} sections)")

        if _has_setup_instructions(readme):
            ux_evidence_parts.append("Setup instructions included")
        else:
            ux_score -= 1
            ux_evidence_parts.append("No clear setup instructions in README")

        if _has_architecture_diagram(readme):
            ux_score += 1
            ux_evidence_parts.append("Architecture diagram or flow description found")
    else:
        ux_score -= 2
        ux_evidence_parts.append("No README available (repo private or inaccessible)")

    # Red flag: No README or empty README
    if not has_readme:
        ux_score = min(ux_score, 4)

    ux_score = max(1, min(10, ux_score))
    ux_evidence = ". ".join(ux_evidence_parts) if ux_evidence_parts else "Basic presentation"

    # --- Reliability & Safety ---
    rel_score = 5
    rel_evidence_parts = []

    if _has_security(all_text):
        rel_score += 1
        sec_kw = _has_keyword(all_text, [".env", "environment variable", "oauth", "gitignore", "credential"])
        rel_evidence_parts.append(f"Security considerations: {', '.join(set(sec_kw))}")

    if _has_error_handling(all_text):
        rel_score += 1
        rel_evidence_parts.append("Error handling documented")

    if _has_tests(all_text):
        rel_score += 2
        rel_evidence_parts.append("Testing documented (automated tests)")
    else:
        rel_evidence_parts.append("No automated tests mentioned")

    cl = sub.get("submission_checklist") or {}
    no_secrets = cl.get("My code does not contain hardcoded API keys or secrets", False)
    if no_secrets:
        rel_evidence_parts.append("Checklist confirms no hardcoded secrets")
    else:
        rel_score -= 1
        rel_evidence_parts.append("Hardcoded secrets concern (checklist not confirmed)")

    # Red flag: API keys visible
    if _has_keyword(all_text, ["hardcoded", "api key visible", "secret in code"]):
        rel_score = min(rel_score, 3)
        rel_evidence_parts.append("RED FLAG: Potential hardcoded secrets detected")

    rel_score = max(1, min(10, rel_score))
    rel_evidence = ". ".join(rel_evidence_parts) if rel_evidence_parts else "Basic reliability measures"

    # --- Weighted total ---
    criteria_scores = {
        "Accuracy & Relevance": acc_score,
        "Reasoning & Multi-step Thinking": reas_score,
        "Creativity & Originality": cre_score,
        "UX & Presentation": ux_score,
        "Reliability & Safety": rel_score,
    }
    evidence = {
        "Accuracy & Relevance": acc_evidence,
        "Reasoning & Multi-step Thinking": reas_evidence,
        "Creativity & Originality": cre_evidence,
        "UX & Presentation": ux_evidence,
        "Reliability & Safety": rel_evidence,
    }
    weights = {"Accuracy & Relevance": 0.222, "Reasoning & Multi-step Thinking": 0.222,
               "Creativity & Originality": 0.167, "UX & Presentation": 0.167,
               "Reliability & Safety": 0.222}

    # Apply repo analysis signals
    criteria_scores, evidence, repo_red_flags, repo_bonus = _apply_repo_signals(
        criteria_scores, evidence, repo_tree, sub
    )
    # Recalculate weighted total after repo adjustments
    weighted_total = round(sum(criteria_scores[c] * weights[c] for c in criteria_scores) * 10, 1)

    result = _build_result(sub, criteria_scores, evidence, weights, weighted_total)
    result["red_flags_detected"].extend(repo_red_flags)
    result["bonus_signals_detected"].extend(repo_bonus)
    return result


def score_reasoning_agents(sub: dict, rubric: dict, repo_tree: dict | None = None) -> dict:
    readme = sub.get("readme_content") or ""
    all_text = _all_text(sub)
    desc = sub.get("description") or ""
    tech_highlights = sub.get("technical_highlights") or ""
    demo_type = _demo_quality(sub)
    has_readme = bool(readme)
    readme_sections = _count_sections(readme) if has_readme else 0
    checklist_r = _checklist_ratio(sub)
    techs = sub.get("technologies") or []

    # --- Accuracy & Relevance ---
    acc_score = 5
    acc_evidence_parts = []

    foundry_kw = _has_keyword(all_text, ["foundry", "microsoft foundry", "azure ai foundry"])
    if foundry_kw:
        acc_score += 2
        acc_evidence_parts.append(f"Foundry usage: {', '.join(set(foundry_kw))}")
    else:
        acc_score -= 1
        acc_evidence_parts.append("No explicit Foundry usage evidence")

    if checklist_r >= 0.8:
        acc_score += 1
        acc_evidence_parts.append(f"Checklist: {int(checklist_r*100)}% met")

    comm_kw = _has_keyword(all_text, ["communication", "social media", "content", "marketing", "campaign"])
    if comm_kw:
        acc_score += 1
        acc_evidence_parts.append(f"Communication/content scenario: {', '.join(set(comm_kw))}")

    grounding_kw = _has_keyword(all_text, ["grounding", "rag", "retrieval", "knowledge base", "search"])
    if grounding_kw:
        acc_score += 1
        acc_evidence_parts.append(f"Grounding: {', '.join(set(grounding_kw))}")

    if not sub.get("repo_url"):
        acc_score -= 2
        acc_evidence_parts.append("No repository URL")

    acc_score = max(1, min(10, acc_score))
    acc_evidence = ". ".join(acc_evidence_parts) if acc_evidence_parts else "Basic scenario coverage"

    # --- Reasoning & Multi-step Thinking ---
    reas_score = 5
    reas_evidence_parts = []

    cot_kw = _has_keyword(all_text, ["chain-of-thought", "cot", "step-by-step reasoning"])
    if cot_kw:
        reas_score += 2
        reas_evidence_parts.append(f"CoT pattern: {', '.join(set(cot_kw))}")

    react_kw = _has_keyword(all_text, ["react", "observe", "think", "act"])
    if react_kw:
        reas_score += 1
        reas_evidence_parts.append(f"ReAct signals: {', '.join(set(react_kw))}")

    reflection_kw = _has_keyword(all_text, ["self-reflection", "self-correct", "evaluate", "review own"])
    if reflection_kw:
        reas_score += 2
        reas_evidence_parts.append(f"Self-reflection: {', '.join(set(reflection_kw))}")

    multi_step_kw = _has_keyword(all_text, ["multi-step", "pipeline", "workflow", "orchestrat", "state management"])
    if multi_step_kw:
        reas_score += 1
        reas_evidence_parts.append(f"Multi-step flow: {', '.join(set(multi_step_kw))}")

    if not cot_kw and not react_kw and not reflection_kw and not multi_step_kw:
        reas_score -= 1
        reas_evidence_parts.append("No explicit reasoning patterns documented")

    # Red flag: No reasoning chain
    if not _has_reasoning(all_text) and not _has_multi_agent(all_text):
        reas_score = min(reas_score, 4)
        reas_evidence_parts.append("RED FLAG: No reasoning chain visible")

    reas_score = max(1, min(10, reas_score))
    reas_evidence = ". ".join(reas_evidence_parts) if reas_evidence_parts else "Limited reasoning documentation"

    # --- Creativity & Originality ---
    cre_score = 5
    cre_evidence_parts = []

    novelty_kw = _has_keyword(all_text, ["novel", "innovative", "unique", "custom", "differentiator"])
    if novelty_kw:
        cre_score += 1
        cre_evidence_parts.append(f"Innovation signals: {', '.join(set(novelty_kw))}")

    if len(techs) >= 3:
        cre_score += 1
        cre_evidence_parts.append(f"Technology stack: {', '.join(techs[:5])}")

    if len(desc) > 200:
        cre_score += 1
        cre_evidence_parts.append("Detailed problem description")

    original_kw = _has_keyword(all_text, [
        "brand", "persona", "strategy", "compliance", "governance",
        "multi-language", "sentiment", "compliance", "regulation",
    ])
    if original_kw:
        cre_score += 1
        cre_evidence_parts.append(f"Domain-specific approach: {', '.join(set(original_kw))}")

    cre_score = max(1, min(10, cre_score))
    cre_evidence = ". ".join(cre_evidence_parts) if cre_evidence_parts else "Standard approach"

    # --- User Experience & Presentation ---
    ux_score = 5
    ux_evidence_parts = []

    if demo_type == "video":
        ux_score += 2
        ux_evidence_parts.append("Video demo available")
    elif demo_type in ("screenshots", "url"):
        ux_score += 1
        ux_evidence_parts.append(f"Demo: {demo_type}")
    else:
        ux_score -= 2
        ux_evidence_parts.append("No demo materials")

    if has_readme:
        if readme_sections >= 6:
            ux_score += 2
            ux_evidence_parts.append(f"Detailed README ({readme_sections} sections)")
        elif readme_sections >= 3:
            ux_score += 1
            ux_evidence_parts.append(f"README with {readme_sections} sections")
        if _has_setup_instructions(readme):
            ux_evidence_parts.append("Setup instructions present")
        if _has_architecture_diagram(readme):
            ux_score += 1
            ux_evidence_parts.append("Architecture or flow diagram included")
    else:
        ux_score -= 2
        ux_evidence_parts.append("No README (repo inaccessible)")

    ux_score = max(1, min(10, ux_score))
    ux_evidence = ". ".join(ux_evidence_parts) if ux_evidence_parts else "Basic presentation"

    # --- Technical Implementation ---
    tech_score = 5
    tech_evidence_parts = []

    if _has_error_handling(all_text):
        tech_score += 1
        tech_evidence_parts.append("Error handling documented")

    if _has_tests(all_text):
        tech_score += 2
        tech_evidence_parts.append("Automated tests present")

    if _has_security(all_text):
        tech_score += 1
        tech_evidence_parts.append("Security measures documented")

    if _has_multi_agent(all_text):
        tech_score += 1
        tech_evidence_parts.append("Multi-agent or tool integration architecture")

    if _has_code_blocks(readme):
        tech_evidence_parts.append("Code examples in README")

    if not sub.get("repo_url"):
        tech_score -= 2
        tech_evidence_parts.append("No repository URL")

    tech_score = max(1, min(10, tech_score))
    tech_evidence = ". ".join(tech_evidence_parts) if tech_evidence_parts else "Basic implementation"

    # --- Weighted total ---
    criteria_scores = {
        "Accuracy & Relevance": acc_score,
        "Reasoning & Multi-step Thinking": reas_score,
        "Creativity & Originality": cre_score,
        "User Experience & Presentation": ux_score,
        "Technical Implementation": tech_score,
    }
    evidence = {
        "Accuracy & Relevance": acc_evidence,
        "Reasoning & Multi-step Thinking": reas_evidence,
        "Creativity & Originality": cre_evidence,
        "User Experience & Presentation": ux_evidence,
        "Technical Implementation": tech_evidence,
    }
    weights = {"Accuracy & Relevance": 0.25, "Reasoning & Multi-step Thinking": 0.25,
               "Creativity & Originality": 0.20, "User Experience & Presentation": 0.15,
               "Technical Implementation": 0.15}

    # Apply repo analysis signals
    criteria_scores, evidence, repo_red_flags, repo_bonus = _apply_repo_signals(
        criteria_scores, evidence, repo_tree, sub
    )
    # Recalculate weighted total after repo adjustments
    weighted_total = round(sum(criteria_scores[c] * weights[c] for c in criteria_scores) * 10, 1)

    result = _build_result(sub, criteria_scores, evidence, weights, weighted_total)
    result["red_flags_detected"].extend(repo_red_flags)
    result["bonus_signals_detected"].extend(repo_bonus)
    return result


def score_enterprise_agents(sub: dict, rubric: dict, repo_tree: dict | None = None) -> dict:
    readme = sub.get("readme_content") or ""
    all_text = _all_text(sub)
    desc = sub.get("description") or ""
    demo_type = _demo_quality(sub)
    has_readme = bool(readme)
    readme_sections = _count_sections(readme) if has_readme else 0
    techs = sub.get("technologies") or []

    # --- Technical Implementation ---
    tech_score = 5
    tech_evidence_parts = []

    m365_kw = _has_keyword(all_text, ["m365", "microsoft 365", "copilot chat", "teams", "sharepoint", "outlook"])
    if m365_kw:
        tech_score += 2
        tech_evidence_parts.append(f"M365 integration: {', '.join(set(m365_kw))}")

    mcp_kw = _has_keyword(all_text, ["mcp server", "mcp", "mcp read", "mcp write"])
    if mcp_kw:
        tech_score += 1
        tech_evidence_parts.append(f"MCP: {', '.join(set(mcp_kw))}")

    oauth_kw = _has_keyword(all_text, ["oauth", "sso", "authentication", "token"])
    if oauth_kw:
        tech_score += 1
        tech_evidence_parts.append(f"Auth: {', '.join(set(oauth_kw))}")

    adaptive_kw = _has_keyword(all_text, ["adaptive card", "card", "adaptive"])
    if adaptive_kw:
        tech_score += 1
        tech_evidence_parts.append(f"Adaptive Cards: {', '.join(set(adaptive_kw))}")

    if not sub.get("repo_url"):
        tech_score -= 2
        tech_evidence_parts.append("No repo URL")

    # Red flag: No M365
    if not m365_kw:
        tech_score = min(tech_score, 4)
        tech_evidence_parts.append("RED FLAG: No M365 integration evidence")

    tech_score = max(1, min(10, tech_score))
    tech_evidence = ". ".join(tech_evidence_parts) if tech_evidence_parts else "Basic implementation"

    # --- Business Value ---
    biz_score = 5
    biz_evidence_parts = []

    biz_kw = _has_keyword(all_text, ["roi", "kpi", "productivity", "efficiency", "cost saving", "time saving", "business"])
    if biz_kw:
        biz_score += 1
        biz_evidence_parts.append(f"Business value signals: {', '.join(set(biz_kw))}")

    enterprise_kw = _has_keyword(all_text, ["enterprise", "compliance", "governance", "workflow", "process"])
    if enterprise_kw:
        biz_score += 1
        biz_evidence_parts.append(f"Enterprise scenario: {', '.join(set(enterprise_kw))}")

    if len(desc) > 200:
        biz_score += 1
        biz_evidence_parts.append("Detailed business description")

    biz_score = max(1, min(10, biz_score))
    biz_evidence = ". ".join(biz_evidence_parts) if biz_evidence_parts else "Limited business case"

    # --- Innovation & Creativity ---
    inno_score = 5
    inno_evidence_parts = []

    if len(techs) >= 3:
        inno_score += 1
        inno_evidence_parts.append(f"Technology stack: {', '.join(techs[:5])}")

    graph_kw = _has_keyword(all_text, ["graph api", "microsoft graph", "graph"])
    if graph_kw:
        inno_score += 1
        inno_evidence_parts.append("Microsoft Graph integration")

    novelty_kw = _has_keyword(all_text, ["novel", "innovative", "creative", "unique"])
    if novelty_kw:
        inno_score += 1
        inno_evidence_parts.append(f"Innovation signals: {', '.join(set(novelty_kw))}")

    if demo_type in ("video", "url"):
        inno_evidence_parts.append(f"Demo type: {demo_type}")

    if has_readme and readme_sections >= 5:
        inno_evidence_parts.append(f"Documentation quality: {readme_sections} README sections")

    inno_score = max(1, min(10, inno_score))
    inno_evidence = ". ".join(inno_evidence_parts) if inno_evidence_parts else "Standard approach"

    # --- Weighted total ---
    criteria_scores = {
        "Technical Implementation": tech_score,
        "Business Value": biz_score,
        "Innovation & Creativity": inno_score,
    }
    evidence_map = {
        "Technical Implementation": tech_evidence,
        "Business Value": biz_evidence,
        "Innovation & Creativity": inno_evidence,
    }
    weights = {"Technical Implementation": 0.33, "Business Value": 0.33, "Innovation & Creativity": 0.34}

    # Apply repo analysis signals
    criteria_scores, evidence_map, repo_red_flags, repo_bonus = _apply_repo_signals(
        criteria_scores, evidence_map, repo_tree, sub
    )
    # Recalculate weighted total after repo adjustments
    weighted_total = round(sum(criteria_scores[c] * weights[c] for c in criteria_scores) * 10, 1)

    result = _build_result(sub, criteria_scores, evidence_map, weights, weighted_total)
    result["red_flags_detected"].extend(repo_red_flags)
    result["bonus_signals_detected"].extend(repo_bonus)
    return result


def _build_result(sub: dict, criteria_scores: dict, evidence: dict, weights: dict, weighted_total: float) -> dict:
    # Build strengths from positive evidence
    strengths = []
    improvements = []
    for crit, ev in evidence.items():
        score = criteria_scores[crit]
        if score >= 7:
            strengths.append(f"{crit}: {ev[:120]}")
        if score <= 5:
            improvements.append(f"{crit}: {ev[:120]}")

    # Ensure at least 2 improvements
    if len(improvements) < 2:
        for crit, score in criteria_scores.items():
            if score <= 6 and crit not in [i.split(":")[0] for i in improvements]:
                improvements.append(f"Consider strengthening {crit} (scored {score}/10)")
            if len(improvements) >= 2:
                break
    if len(improvements) < 2:
        improvements.append("Consider adding automated tests")
        improvements.append("Consider adding architecture documentation")

    # Red flags
    red_flags = []
    bonus_signals = []
    all_text = _all_text(sub).lower()
    if not sub.get("readme_content"):
        red_flags.append("No README or inaccessible repository")
    if not sub.get("has_demo"):
        red_flags.append("No working demo provided")
    if "mcp" in all_text:
        bonus_signals.append("MCP integration found")
    if "test" in all_text or "pytest" in all_text:
        bonus_signals.append("Automated tests present")

    # Summary
    desc = sub.get("description") or sub.get("title") or ""
    summary_text = desc[:200] if len(desc) > 200 else desc
    summary = f"{sub.get('project_name', 'Unknown')} ({sub.get('track', '?')} track, {weighted_total}/100): {summary_text}"
    if len(summary) > 350:
        summary = summary[:347] + "..."

    # Confidence
    has_readme = bool(sub.get("readme_content"))
    has_demo = sub.get("has_demo", False)
    confidence = "high" if has_readme and has_demo else "medium" if has_readme or has_demo else "low"

    return {
        "issue_number": sub["issue_number"],
        "project_name": sub.get("project_name", "Unknown"),
        "track": sub.get("track", "unknown"),
        "issue_url": sub.get("issue_url", ""),
        "github_username": sub.get("github_username", ""),
        "criteria_scores": criteria_scores,
        "evidence": evidence,
        "confidence": confidence,
        "red_flags_detected": red_flags,
        "bonus_signals_detected": bonus_signals,
        "weighted_total": weighted_total,
        "strengths": strengths[:5],
        "improvements": improvements[:5],
        "summary": summary,
    }


SCORERS = {
    "creative-apps": score_creative_apps,
    "reasoning-agents": score_reasoning_agents,
    "enterprise-agents": score_enterprise_agents,
}


async def main():
    # Load collected submissions
    with open("data/collected_submissions.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    submissions = data["submissions"]
    print(f"Loaded {len(submissions)} submissions")

    # Load rubrics
    rubrics = {}
    for track in ["creative-apps", "reasoning-agents", "enterprise-agents"]:
        rubrics[track] = await get_scoring_rubric(track)
        print(f"Loaded rubric: {track} ({len(rubrics[track]['criteria'])} criteria)")

    # Import repo tree fetcher
    from saiten_mcp.tools.submissions import fetch_repo_tree

    # Fetch repo trees for all submissions (with rate limiting)
    print("\nFetching repository trees for code analysis...")
    repo_trees: dict[int, dict | None] = {}
    for sub in submissions:
        issue_num = sub.get("issue_number", 0)
        repo_url = sub.get("repo_url")
        if repo_url:
            try:
                tree = await fetch_repo_tree(repo_url)
                repo_trees[issue_num] = tree
                if tree:
                    src = tree.get("total_source_files", 0)
                    tst = tree.get("total_test_files", 0)
                    commits = tree.get("commit_count", 0)
                    print(f"  #{issue_num}: {src} source, {tst} test, {commits} commits")
                else:
                    print(f"  #{issue_num}: repo inaccessible")
            except Exception as exc:
                print(f"  #{issue_num}: fetch error: {exc}")
                repo_trees[issue_num] = None
        else:
            print(f"  #{issue_num}: no repo URL")
            repo_trees[issue_num] = None

    # Score each submission with repo analysis
    print("\nScoring submissions with repo analysis...")
    all_scores = []
    for sub in submissions:
        track = sub.get("track", "unknown")
        scorer = SCORERS.get(track)
        if not scorer:
            print(f"SKIP: #{sub['issue_number']} ({sub.get('project_name')}) - unknown track: {track}")
            continue

        issue_num = sub.get("issue_number", 0)
        tree = repo_trees.get(issue_num)
        result = scorer(sub, rubrics[track], repo_tree=tree)
        all_scores.append(result)
        flags = result.get("red_flags_detected", [])
        flag_str = f" [FLAGS: {', '.join(flags[:2])}]" if flags else ""
        print(f"SCORED: #{result['issue_number']} {result['project_name']} ({track}) = {result['weighted_total']}{flag_str}")

    # Save all scores
    print(f"\nSaving {len(all_scores)} scores...")
    save_result = await save_scores(all_scores)
    print(f"Save result: {json.dumps(save_result, indent=2)}")

    # Summary stats by track
    print("\n=== SCORING SUMMARY ===")
    for track in ["creative-apps", "reasoning-agents", "enterprise-agents"]:
        track_scores = [s for s in all_scores if s["track"] == track]
        if track_scores:
            totals = [s["weighted_total"] for s in track_scores]
            mean = sum(totals) / len(totals)
            min_s = min(totals)
            max_s = max(totals)
            print(f"{track}: n={len(track_scores)}, mean={mean:.1f}, min={min_s}, max={max_s}")


asyncio.run(main())
