"""Phase B: AI Qualitative Review — score adjustments.

Applies evidence-based adjustments to baseline (Phase A) scores.
Each adjustment must include ai_review_notes with rationale.

Usage:
    python scripts/ai_review.py
"""

import asyncio
import json
import sys

sys.path.insert(0, "src")
from saiten_mcp.tools.scores import adjust_scores

adjustments = [
    # === REASONING-AGENTS ===
    {
        "issue_number": 27,
        "ai_review_notes": "TrendSurf: Excellent 4-agent pipeline with real Azure OpenAI, WorkIQ M365, and brand policy vector store. Slight downgrade on Accuracy (narrow social media domain).",
        "criteria_scores": {"Accuracy & Relevance": 9},
        "summary": "Multi-agent social media pipeline for regulated industries with 4 specialized agents chaining reasoning patterns (ReAct, CoT, Structured Generation, Self-Reflection), brand policy enforcement via vector store, and WorkIQ M365 data integration.",
        "strengths": [
            "Genuine multi-agent pipeline with 4 distinct reasoning patterns",
            "WorkIQ integration pulls real M365 context",
            "Brand Guard uses vector store for semantic compliance checking",
            "Comprehensive README with screenshots",
        ],
        "improvements": [
            "Could add automated testing for agent outputs",
            "Brand policy enforcement could include more configurable rules",
        ],
    },
    {
        "issue_number": 58,
        "ai_review_notes": "StoryCircuit: Strong 35-file codebase with 987-line knowledge base and MCP tools. Dockerized deployment. BUT it is another social media content generator - domain overlap with #27, #38, #43, #12. Creativity downgraded for crowded domain.",
        "criteria_scores": {"Accuracy & Relevance": 9, "Creativity & Originality": 7},
        "summary": "Technical narrative architect transforming complex topics into platform-optimized social media content via Azure AI Foundry. Features MCP tool integration for Microsoft Docs search, 987-line knowledge base for CoT reasoning, containerized deployment. Strong engineering but shares crowded social media content domain.",
        "strengths": [
            "Large knowledge base (987 lines) for Chain-of-Thought reasoning",
            "MCP tool integration for real-time Microsoft Docs search",
            "Containerized deployment with Dockerfile",
            "35 source files with 8 commits",
        ],
        "improvements": [
            "Differentiate from other social media content tools in cohort",
            "Add evaluation metrics for content quality",
            "Expand beyond social media generation",
        ],
    },
    {
        "issue_number": 38,
        "ai_review_notes": "Zavatravel: Similar concept to #27 (social media content). GroupChat orchestration genuine but domain overlap. Tech Implementation downgraded.",
        "criteria_scores": {
            "Accuracy & Relevance": 9,
            "Creativity & Originality": 7,
            "Technical Implementation": 8,
        },
        "summary": "Multi-agent GroupChat social media content creator with Creator (CoT), Reviewer (ReAct), and Publisher (Self-Reflection) agents. Features Azure OpenAI + Copilot SDK hybrid, React frontend, brand guidelines grounding.",
        "strengths": [
            "Three distinct agents with different reasoning patterns",
            "Full-stack with React frontend and Fluent UI",
            "Brand guidelines grounding via vector store",
        ],
        "improvements": [
            "Only 2 commits - limited iterative development evidence",
            "Concept overlaps with other social media agents",
            "No test files",
        ],
    },
    {
        "issue_number": 60,
        "ai_review_notes": "BrandComm-agent: Full-stack React+ASP.NET+Foundry with Entra ID auth. 52 source files, 15 commits. Solid engineering but narrow social media domain. No tests despite test claim.",
        "criteria_scores": {"Technical Implementation": 8},
        "summary": "Full-stack BrandComm agent with React 19 + ASP.NET Core 9, Entra ID PKCE auth, and Azure AI Foundry v2 Agent integration for brand-compliant social media content. 52 source files, 15 commits, Azure Container Apps deployment via azd.",
        "strengths": [
            "Full-stack implementation with React 19 + ASP.NET Core 9",
            "Entra ID authentication with PKCE flow",
            "Azure Container Apps deployment via azd up",
            "CELA compliance rules for content guardrails",
        ],
        "improvements": [
            "Add automated tests (0 test files despite claims)",
            "Document the reasoning pattern used (CoT/ReAct/etc.)",
            "Add demo screenshots or video",
        ],
    },
    {
        "issue_number": 43,
        "ai_review_notes": "Nimbus Content Agent: Decent BFSI agent but 1 commit, 0 tests. Accuracy and TechImpl downgraded.",
        "criteria_scores": {"Accuracy & Relevance": 8, "Technical Implementation": 6},
        "summary": "BFSI social media content agent using Microsoft Foundry SDK with knowledge base grounding on brand guidelines and industry data, extensible via MCP tool hooks.",
        "strengths": [
            "Domain-specific BFSI focus with brand grounding",
            "Knowledge base with source attribution",
            "Extensible MCP tool architecture",
        ],
        "improvements": [
            "Only 1 commit with no tests",
            "Technical highlights are minimal",
            "No CI/CD or automated testing",
        ],
    },
    {
        "issue_number": 35,
        "ai_review_notes": "Policy compliance checker: Full-stack React + .NET 8 + AI Foundry. Complex GDPR domain. Reasoning upgraded, TechImpl downgraded (1 commit).",
        "criteria_scores": {
            "Reasoning & Multi-step Thinking": 8,
            "Technical Implementation": 8,
        },
        "summary": "GDPR privacy notice copilot with full-stack architecture (React/TS, .NET 8, Azure AI Foundry) guiding users through all 13 mandatory Article 13/14 fields via conversational chat.",
        "strengths": [
            "Full-stack MVP with React + .NET 8",
            "Deep GDPR domain knowledge (13 Article 13/14 fields)",
            "User-friendly conversational approach",
        ],
        "improvements": [
            "Only 1 commit limits verification",
            "Could add test coverage for compliance edge cases",
        ],
    },
    {
        "issue_number": 47,
        "ai_review_notes": "SK/AutoGen to MAF Modernizer: Strong concept, real utility. 23 commits shows iteration. Reasoning upgraded.",
        "criteria_scores": {"Accuracy & Relevance": 9, "Reasoning & Multi-step Thinking": 8},
        "summary": "MCP-exposed code modernization agent that transforms Semantic Kernel and AutoGen code to Microsoft Agent Framework, usable standalone or as composable agent-callable capability.",
        "strengths": [
            "Genuine utility for framework modernization",
            "23 commits show iterative development",
            "MCP exposure makes it composable",
        ],
        "improvements": [
            "Could expand framework coverage",
            "More modernization accuracy metrics needed",
        ],
    },
    {
        "issue_number": 18,
        "ai_review_notes": "My Proposal Develop: Large README but only 4 source files and 0 test files despite claims. Gap between docs and implementation.",
        "criteria_scores": {"Technical Implementation": 5, "Accuracy & Relevance": 8},
        "summary": "RFP proposal agent with Foundry IQ. Documentation-heavy (47 README sections) but only 4 source files and no test files, creating a gap between documentation ambition and actual implementation.",
        "strengths": [
            "Comprehensive documentation",
            "Azure AI Foundry integration",
            "Practical RFP business scenario",
        ],
        "improvements": [
            "Add test files described in documentation",
            "Increase source code",
            "Include CI/CD configuration",
        ],
    },
    # === CREATIVE-APPS ===
    {
        "issue_number": 32,
        "ai_review_notes": "SovereignFit: Strong MCP pipeline with 34 tests. But only 1 commit despite 4000+ lines raises template concerns. Reliability downgraded.",
        "criteria_scores": {"Reliability & Safety": 7},
        "summary": "Multi-agent Azure deployment recommender evaluating 5 models across 5 dynamically weighted dimensions with MCP server integration, rich terminal UI, and 34 automated tests.",
        "strengths": [
            "Dynamic weight adjustment based on workload signals is novel",
            "MCP server with 5 tools for Copilot integration",
            "34 pytest tests across 4 agents",
        ],
        "improvements": [
            "Only 1 commit despite 4000+ lines - hard to verify iterative development",
            "Consider multi-commit workflow for credibility",
        ],
    },
    {
        "issue_number": 23,
        "ai_review_notes": "repo-analyzer: Solid tool with impressive 19 test files. Reliability 10 downgraded.",
        "criteria_scores": {"Reliability & Safety": 8},
        "summary": "GitHub repository analyzer combining deterministic metrics with LLM-powered intelligence to surface risks, knowledge silos, and code quality insights across people, security, and team dynamics.",
        "strengths": [
            "Excellent test coverage with 19 test files",
            "DevContainer for consistent environment",
            "Multi-dimensional analysis (people, code, security, team)",
        ],
        "improvements": [
            "Heavy AI code generation acknowledged - originality concern",
            "Could add explicit error handling documentation",
        ],
    },
    {
        "issue_number": 42,
        "ai_review_notes": "Zava Smart Assistant: Well-structured with innovative Markdown-driven skill system. 181 tests is exceptional. No criteria changes.",
        "summary": "AI enterprise incident response agent using Copilot SDK with novel Markdown-driven skill pipeline, guiding users through Diagnose/Fix/Verify/Report phases with 181 automated tests.",
        "strengths": [
            "181 automated tests - exceptional coverage",
            "Markdown-driven skill system is genuinely innovative",
            "GPT-4.1 routing with MCP integration",
        ],
        "improvements": [
            "Could document skill pipeline architecture more clearly",
            "Error handling for edge cases in incident response",
        ],
    },
    {
        "issue_number": 31,
        "ai_review_notes": "Threat Incident Swarm Commander: Creative Matrix theme but 6593 files (likely node_modules). Accuracy/UX/Reliability downgraded.",
        "criteria_scores": {
            "Accuracy & Relevance": 7,
            "UX & Presentation": 8,
            "Reliability & Safety": 6,
        },
        "summary": "Matrix-themed autonomous swarm AI simulation modeling cascading incident response, with dual UI (terminal + React Canvas) and MCP integration for Copilot Chat control.",
        "strengths": [
            "Highly creative Matrix metaphor for incident response",
            "Dual UI with code rain visualization",
            "MCP integration for Copilot Chat",
        ],
        "improvements": [
            "6593 files suggests vendor/node_modules included",
            "30 min dev time raises quality concerns",
            "No production-relevant incident response logic",
        ],
    },
    {
        "issue_number": 34,
        "ai_review_notes": "LearnIQ: 21 source files but Accuracy 10 too high - no learning outcome verification. No tests.",
        "criteria_scores": {"Accuracy & Relevance": 8},
        "summary": "AI-powered adaptive learning platform with personalized content delivery and progress tracking using GitHub Copilot SDK.",
        "strengths": [
            "21 source files showing substantial implementation",
            "Personalized learning approach",
        ],
        "improvements": [
            "No test files - essential for educational platforms",
            "Only 3 commits",
        ],
    },
    {
        "issue_number": 49,
        "ai_review_notes": "EasyExpenseAI: 19 source files. UX 10 too high without exceptional evidence.",
        "criteria_scores": {"UX & Presentation": 8},
        "summary": "AI expense tracking app with receipt scanning and categorization, featuring mobile-first design built with Copilot SDK.",
        "strengths": [
            "19 source files showing substantial implementation",
            "Mobile-first design approach",
        ],
        "improvements": [
            "Only 1 commit suggests possible template",
            "No test files",
        ],
    },
    {
        "issue_number": 45,
        "ai_review_notes": "Prompt Escape: Genuinely creative escape room game. Creativity UNDER-scored at 7 - upgraded to 9.",
        "criteria_scores": {"Creativity & Originality": 9},
        "summary": "Visual prompt-engineering escape room game with 3 themed adventures where players write AI prompts to solve puzzles, combining gamification with AI education.",
        "strengths": [
            "Genuinely creative gamification of prompt engineering",
            "Multiple themed adventures with escalating difficulty",
            "Visual storytelling with immersive narratives",
        ],
        "improvements": [
            "Only 1 commit raises template concerns",
            "No test files for puzzle logic",
        ],
    },
    {
        "issue_number": 55,
        "ai_review_notes": "kube-copilot: Genuinely useful TUI. 11 commits shows iteration. Creativity upgraded for innovative Copilot+K8s combination.",
        "criteria_scores": {"Creativity & Originality": 8},
        "summary": "Terminal UI for natural-language Kubernetes cluster management via Copilot SDK. 15 source files, 11 commits showing genuine iterative development.",
        "strengths": [
            "Genuinely useful tool replacing complex kubectl commands",
            "Real TUI implementation with interactive interface",
            "11 commits showing iterative development",
            "Creative Copilot SDK + Kubernetes combination",
        ],
        "improvements": [
            "Add more automated tests beyond single test file",
            "Include architecture documentation",
            "Add error recovery examples",
        ],
    },
    {
        "issue_number": 39,
        "ai_review_notes": "CodeIntel: 8 source files, 1 commit. MCP + WorkIQ combination interesting. Reliability adjusted.",
        "criteria_scores": {"Reliability & Safety": 6},
        "summary": "Team intelligence hub combining GitHub analytics with M365 WorkIQ insights. Features 8 MCP tools for Copilot, REST API, CLI.",
        "strengths": [
            "MCP + WorkIQ M365 data combination is interesting",
            "Multi-interface: MCP server + REST API + CLI",
            "8 source files showing real implementation",
        ],
        "improvements": [
            "Only 1 commit suggests possible template or code dump",
            "Add automated tests",
            "Include .env.example for configuration",
        ],
    },
    {
        "issue_number": 11,
        "ai_review_notes": "Hybrid DNS Copilot: Good MCP server. No working demo. UX downgraded.",
        "criteria_scores": {"UX & Presentation": 7},
        "summary": "Interactive Azure DNS Private Resolver visualizer with MCP server for GitHub Copilot. 11 source files, good documentation but no working demo evidence.",
        "strengths": [
            "MCP server integration for GitHub Copilot",
            "Detailed documentation with architecture",
            "11 source files",
        ],
        "improvements": [
            "Add working demo video or screenshots",
            "Add automated tests",
            "Provide usage examples",
        ],
    },
    {
        "issue_number": 22,
        "ai_review_notes": "DailySync: 13 source files, useful tool. Only 3 commits, no demo. UX and Reliability downgraded.",
        "criteria_scores": {"UX & Presentation": 7, "Reliability & Safety": 6},
        "summary": "AI-powered CLI for daily standup report generation from GitHub and M365 data. Good concept with 13 source files but lacks demo and has only 3 commits.",
        "strengths": [
            "Practical developer productivity concept",
            "Combines GitHub and M365 data sources",
            "13 source files",
        ],
        "improvements": [
            "Add working demo video",
            "Increase commit history",
            "Add automated tests",
        ],
    },
    {
        "issue_number": 30,
        "ai_review_notes": "PolicyShield: No README, 1 commit. Accuracy downgraded.",
        "criteria_scores": {"Accuracy & Relevance": 6},
        "summary": "Enterprise policy-as-code Next.js web app. Interesting concept but no README and 1 commit.",
        "strengths": [
            "Policy-as-code concept for enterprise compliance",
            "Description mentions MCP integration",
        ],
        "improvements": [
            "Add comprehensive README",
            "Use multiple commits",
            "Make repository accessible",
        ],
    },
    {
        "issue_number": 26,
        "ai_review_notes": "Bridgenote: No README, 2 commits. Accuracy and UX downgraded.",
        "criteria_scores": {"Accuracy & Relevance": 6, "UX & Presentation": 5},
        "summary": "Note transformation assistant for cross-system workflows. No README and only 2 commits.",
        "strengths": [
            "Cross-system note transformation concept",
            "18 source files exist",
        ],
        "improvements": [
            "Add comprehensive README",
            "Provide working demo",
            "Increase development commits",
        ],
    },
    {
        "issue_number": 52,
        "ai_review_notes": "HeadlineArt: Creative concept but thin codebase. No criteria changes.",
        "summary": "AI agent that transforms trending news headlines into visual art.",
        "strengths": [
            "Creative fusion of news and visual art",
            "Unique concept in reasoning-agents track",
        ],
        "improvements": ["Only 1 source file", "Only 4 commits"],
    },
    # === ENTERPRISE-AGENTS ===
    {
        "issue_number": 13,
        "ai_review_notes": "SE Agent: Copilot Studio Power Platform - 0 source files is misleading for no-code. TechImpl and BusinessValue upgraded.",
        "criteria_scores": {"Technical Implementation": 7, "Business Value": 7},
        "summary": "Copilot Studio agent generating Financial Services demo data in D365 Sales/Dataverse.",
        "strengths": [
            "Genuine Copilot Studio + Power Platform architecture",
            "Real D365 FSI use case",
            "Importable Power Platform Solution",
        ],
        "improvements": [
            "No source code files (Power Platform)",
            "Could add customization documentation",
        ],
    },
    {
        "issue_number": 44,
        "ai_review_notes": "Corporate Bullshit Translator: No source code. Concept without implementation.",
        "summary": "M365 Copilot agent concept for translating corporate jargon, but lacks implementation.",
        "strengths": ["Entertaining and relatable concept"],
        "improvements": [
            "README is just one line",
            "No source code files",
            "No working demo",
        ],
    },
    {
        "issue_number": 56,
        "ai_review_notes": "Compliment my pet: Fun but wrong track. 0 source files. Minimal business value.",
        "criteria_scores": {"Business Value": 2},
        "summary": "AI agent for pet compliments. 0 source files. Wrong track assignment (enterprise vs creative).",
        "strengths": [
            "Fun mood-boosting concept",
            "Has README with setup instructions",
        ],
        "improvements": [
            "Add actual source code",
            "Pivot to creative-apps track",
            "Implement MCP integration",
        ],
    },
    {
        "issue_number": 50,
        "ai_review_notes": "Email Summarizer: 2 files, 0 source code. Concept only.",
        "criteria_scores": {"Technical Implementation": 2, "Business Value": 3},
        "summary": "Email inbox summarization concept. Only 2 files with no source code.",
        "strengths": ["Practical email management concept"],
        "improvements": [
            "Add source code",
            "Create M365 integration",
            "Write comprehensive README",
        ],
    },
    # === LOW-QUALITY / SPECIAL ===
    {
        "issue_number": 10,
        "ai_review_notes": "Self-described as doing nothing. Joke entry.",
        "criteria_scores": {
            "Accuracy & Relevance": 3,
            "Creativity & Originality": 1,
            "UX & Presentation": 1,
        },
        "summary": "Self-described as doing nothing. Single file (README only). Joke entry.",
        "strengths": ["Honest description"],
        "improvements": [
            "Implement an actual project",
            "Add source code",
            "Define a clear use case",
        ],
    },
    {
        "issue_number": 19,
        "ai_review_notes": "Architecture Visualizer: Repo inaccessible. Cannot verify.",
        "criteria_scores": {
            "Accuracy & Relevance": 4,
            "Creativity & Originality": 4,
            "UX & Presentation": 4,
        },
        "summary": "PowerPoint slide generator from technical artifacts. Repository inaccessible.",
        "strengths": ["Interesting auto-generation concept"],
        "improvements": [
            "Make repository public",
            "Add README",
            "Provide demo",
        ],
    },
    {
        "issue_number": 9999,
        "ai_review_notes": "Test submission, not a real project.",
        "criteria_scores": {
            "Accuracy & Relevance": 1,
            "Reasoning & Multi-step Thinking": 1,
            "Creativity & Originality": 1,
            "UX & Presentation": 1,
            "Reliability & Safety": 1,
        },
        "summary": "Test submission - not a real project entry.",
        "strengths": [],
        "improvements": [
            "This is a test entry and should be excluded from rankings",
        ],
    },
    # === META / SELF ===
    {
        "issue_number": 54,
        "ai_review_notes": "Saiten: Self-referential scoring system. 15 source, 7 tests, 16 commits. No criteria changes.",
        "summary": "Multi-agent scoring system for Agents League hackathon. 6 Copilot custom agents with Orchestrator-Workers pattern, MCP server, automated pipeline.",
        "strengths": [
            "Novel self-referential meta-project concept",
            "MCP server with 5 tool categories",
            "7 test files and 16 commits show iterative development",
            "Sophisticated multi-agent orchestration pattern",
        ],
        "improvements": [
            "Add demo video or screenshots",
            "Expand README with setup instructions",
            "Handle edge cases in scoring",
        ],
    },
]


async def main() -> None:
    result = await adjust_scores(adjustments)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
