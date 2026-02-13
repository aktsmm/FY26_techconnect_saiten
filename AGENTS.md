<!-- skill-ninja-START -->

## Agent Skills (Compressed Index)

> **IMPORTANT**: Prefer skill-led reasoning over pre-training-led reasoning.
> Read the relevant SKILL.md before working on tasks covered by these skills.

### Skills Index

| Skill                                                                    | Path                     | Description                                                                                          |
| ------------------------------------------------------------------------ | ------------------------ | ---------------------------------------------------------------------------------------------------- |
| [agentic-workflow-guide](.github/skills/agentic-workflow-guide/SKILL.md) | `agentic-workflow-guide` | Design, review, and improve agent workflows & agent using SSOT, SRP, Fail Fast principles. Suppor... |

<!-- skill-ninja-END -->

---

## Agents Index

### Orchestrator

| Agent                                                              | File                  | Description                                                                            |
| ------------------------------------------------------------------ | --------------------- | -------------------------------------------------------------------------------------- |
| [saiten-orchestrator](.github/agents/saiten-orchestrator.agent.md) | `saiten-orchestrator` | Scoring orchestrator — routes user intent, delegates to sub-agents, integrates results |

### Sub-Agents (Workers)

| Agent                                                        | File               | SRP Responsibility                              | MCP Tools                                   |
| ------------------------------------------------------------ | ------------------ | ----------------------------------------------- | ------------------------------------------- |
| [saiten-collector](.github/agents/saiten-collector.agent.md) | `saiten-collector` | Data collection & validation from GitHub Issues | `list_submissions`, `get_submission_detail` |
| [saiten-scorer](.github/agents/saiten-scorer.agent.md)       | `saiten-scorer`    | AI qualitative review & score adjustment        | `get_scoring_rubric`, `adjust_scores`       |
| [saiten-reviewer](.github/agents/saiten-reviewer.agent.md)   | `saiten-reviewer`  | Score consistency review & bias detection       | `get_scoring_rubric`, read scores           |
| [saiten-reporter](.github/agents/saiten-reporter.agent.md)   | `saiten-reporter`  | Ranking report generation & presentation        | `generate_ranking_report`                   |
| [saiten-commenter](.github/agents/saiten-commenter.agent.md) | `saiten-commenter` | GitHub Issue feedback comments (via Handoff)    | `gh issue comment`                          |

### Workflow Patterns

**Orchestrator-Workers + Prompt Chaining + Evaluator-Optimizer + Handoff**

```
User Request
    │
    ▼
┌──────────────────┐
│ @orchestrator    │
│ (Route + Control)│
└────────┬─────────┘
         │
    ┌────▼────┐
    │@collector│  Phase 0: Collect submissions from GitHub Issues
    │(Collect) │  Gate: data OK?
    └────┬────┘
         │
    ┌────▼──────────┐
    │ score_all.py   │  Phase A: Mechanical baseline (orchestrator runs script)
    │ (Python)       │  Keyword matching + repo tree analysis + checklist
    └────┬──────────┘
         │
    ┌────▼────┐
    │ @scorer  │  Phase B: AI qualitative review (Copilot reads submissions)
    │(AI Review│  ★ THIS IS THE AI JUDGMENT STEP ★
    │ 5/batch) │  Reads README/description → adjusts scores via adjust_scores()
    └────┬────┘
         │
    ┌────▼─────┐
    │@reviewer  │  Phase C: Consistency validation (Copilot checks fairness)
    │(Validate) │  Outliers, clustering, bias detection
    └────┬─────┘  Gate: PASS? → If FLAG, re-delegate to @scorer
         │              ▲                    │
         │              └────────────────────┘ (max 2 cycles)
    ┌────▼─────┐
    │@reporter  │  Phase D: Generate ranking report
    │(Report)   │
    └────┬─────┘
         │
    ┌────▼─────┐
    │@commenter │  [Handoff] Human-in-the-Loop (user confirms)
    │(Feedback) │
    └──────────┘
```

**Key: Two-Phase Scoring**

- `score_all.py` = Phase A mechanical baseline (keyword matching, repo tree, checklist)
- `@scorer` = Phase B AI Review — **Copilot agent** reads submissions qualitatively,
  judges novelty/depth/quality, catches keyword gaming, adjusts via `adjust_scores()`
- `@reviewer` = Phase C — **Copilot agent** validates score consistency and fairness

### Design Principles

- **Incremental Collection**: ALWAYS fetch live Issue list from GitHub and compare
  with existing data. Fetch details only for new/updated Issues. Never rely on
  hardcoded Issue number lists.
- **Idempotent & Merge-Based**: Batch scripts MUST be idempotent. Existing data
  is preserved via upsert; never overwrite blindly. Partial runs must not corrupt
  previously collected data.
