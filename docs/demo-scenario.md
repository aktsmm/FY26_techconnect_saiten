# Demo Video Scenario — Saiten Scoring Agent

> Recording guide for the Agents League @ TechConnect submission demo.
> Target length: **3–4 minutes**.

---

## Pre-Recording Checklist

- [ ] VS Code open with this workspace
- [ ] GitHub Copilot Chat panel visible (right sidebar)
- [ ] Terminal panel closed or minimized
- [ ] `data/scores.json` reset or empty (for clean demo)
- [ ] MCP server running (auto-starts via `.vscode/mcp.json`)

---

## Scene 1: Introduction (0:00 – 0:30)

**Visual**: VS Code with README.md open, Copilot Chat panel visible.

**Narration / Caption**:

> "Saiten is a multi-agent scoring system for the Agents League hackathon.
> It uses 6 Copilot custom agents and an MCP server to automatically
> collect, score, review, and report on 43+ submissions — all from
> VS Code's chat panel."

**Action**: Briefly scroll through the README showing the workflow diagram.

---

## Scene 2: Scoring a Single Submission (0:30 – 1:30)

**Prompt to type in Chat**:

```
@saiten-orchestrator score #49
```

**Expected Flow** (show each step appearing in chat):

1. **Orchestrator routes** → delegates to `@saiten-collector`
2. **Collector** fetches Issue #49 (EasyExpenseAI)
   - Shows: Track, repo URL, README length, demo status
   - Gate: ✅ Data complete
3. **Scorer** evaluates with evidence
   - Shows per-criterion scores with evidence citations
   - Example: "Accuracy: 8/10 — 5-agent Semantic Kernel pipeline"
4. **Reviewer** validates
   - Shows: PASS (within 2σ, no generic phrases)
5. **Reporter** generates report
   - Shows: `reports/ranking.md` saved

**Narration / Caption**:

> "Each agent has a single responsibility. The scorer cites specific
> evidence for every criterion — no generic 'good README' phrases allowed."

---

## Scene 3: Scoring All Submissions (1:30 – 2:30)

**Prompt to type in Chat**:

```
@saiten-orchestrator score all
```

**Expected Flow**:

1. **Orchestrator** starts processing 43 submissions
2. **Todo list** appears in VS Code showing progress
   - "Collecting submissions..." → ✅
   - "Scoring Creative Apps (30)..." → ✅
   - "Scoring Reasoning Agents (10)..." → ✅
   - "Scoring Enterprise Agents (3)..." → ✅
   - "Reviewing scores..." → ✅
   - "Generating report..." → ✅
3. **Final output**: Top 10 table with scores
4. **Handoff button** appears: "💬 Post feedback comments to Top 10"

**Narration / Caption**:

> "The Evaluator-Optimizer pattern ensures scoring consistency:
> the reviewer checks for bias and statistical outliers,
> and flags submissions for re-scoring if needed."

---

## Scene 4: Review & Report (2:30 – 3:15)

**Action**: Open `reports/ranking.md` to show the generated report.

**Show**:

- Top 10 overall ranking table
- Per-track champion sections (Creative, Reasoning, Enterprise)
- An individual evaluation summary showing evidence-anchored scores

**Prompt (optional)**:

```
@saiten-orchestrator review scores
```

**Expected output**:

- Bias detection results (5 types checked)
- Score distribution statistics
- Any flagged outliers

**Narration / Caption**:

> "The reviewer agent detects 5 types of bias: central tendency,
> halo effect, leniency, range restriction, and anchoring.
> Flagged scores get sent back for re-evaluation automatically."

---

## Scene 5: Human-in-the-Loop & MCP (3:15 – 3:45)

**Action**: Click the "💬 Post feedback comments to Top 10" Handoff button.

**Show**:

- `@saiten-commenter` generates comment previews
- User confirms before any GitHub Issue comment is posted
- Comment includes score breakdown and improvement suggestions

**Narration / Caption**:

> "Comments are only posted after explicit user confirmation —
> the Human-in-the-Loop pattern ensures no accidental feedback."

**Action**: Show `.vscode/mcp.json` briefly to demonstrate zero-config setup.

---

## Scene 6: Testing & Closing (3:45 – 4:00)

**Action**: Run in terminal:

```bash
python -m pytest tests/ --cov=saiten_mcp -q
```

**Show**: `100 passed, 93% coverage` output.

**Narration / Caption**:

> "100 automated tests with 93% code coverage verify
> every parser, model, tool, and report generator."

---

## Key Points to Highlight

| Feature                       | What to Emphasize                             |
| ----------------------------- | --------------------------------------------- |
| **6 Custom Agents**           | Orchestrator-Workers pattern with SRP         |
| **MCP Server**                | 5 tools, FastMCP, stdio transport             |
| **Evidence-Anchored Scoring** | Every criterion requires cited evidence       |
| **Evaluator-Optimizer**       | Reviewer → re-score feedback loop             |
| **Human-in-the-Loop**         | Handoff for comment posting                   |
| **100 Tests / 93% Coverage**  | pytest + Pydantic validation                  |
| **Zero Config**               | `.vscode/mcp.json` auto-starts MCP            |
| **Copilot Usage**             | Entire agent system built with GitHub Copilot |

---

## Fallback: If Demo Breaks

If the MCP server or GitHub API is slow, you can:

1. Show `data/scores.json` with pre-scored results
2. Show `reports/ranking.md` with the generated report
3. Run `python -m pytest tests/ -q` to demonstrate testing
4. Walk through the agent `.md` files to explain the architecture
