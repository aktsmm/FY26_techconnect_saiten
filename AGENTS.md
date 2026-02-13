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
| [saiten-scorer](.github/agents/saiten-scorer.agent.md)       | `saiten-scorer`    | Rubric-based scoring with quality gate          | `get_scoring_rubric`, `save_scores`         |
| [saiten-reviewer](.github/agents/saiten-reviewer.agent.md)   | `saiten-reviewer`  | Score consistency review & bias detection       | `get_scoring_rubric`, read scores           |
| [saiten-reporter](.github/agents/saiten-reporter.agent.md)   | `saiten-reporter`  | Ranking report generation & presentation        | `generate_ranking_report`                   |
| [saiten-commenter](.github/agents/saiten-commenter.agent.md) | `saiten-commenter` | GitHub Issue feedback comments (via Handoff)    | `gh issue comment`                          |

### Workflow Patterns

**Orchestrator-Workers + Prompt Chaining + Evaluator-Optimizer + Handoff**

```
User Request
    │
    ▼
┌─────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ @saiten-orchestrator │────▶│ @collector│────▶│ @scorer  │────▶│ @reviewer│────▶│ @reporter│
│ (Route)  │     │ (Collect) │     │(Evaluate)│     │(Validate)│     │ (Report) │
└─────────┘     └───────────┘     └──────────┘     └──────────┘     └──────────┘
    │            Gate: data OK?    Gate: OK?    ▲   Gate: PASS?      Gate: OK?
    ▼                                          │       │
 Results ◄─────────────────────────────────────┘───────┘
    │                                Re-score if FLAG
    ▼
 [Handoff Button: 💬 Post Feedback]
    │
    ▼
┌───────────┐
│ @commenter│  ← Human-in-the-Loop (user confirms before posting)
│(Comment)  │
└───────────┘
```
