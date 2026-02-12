# Saiten — 詳細設計書
> **プロジェクト**: Agents League @ TechConnect 採点エージェント
> **バージョン**: 1.0
> **作成日**: 2026-02-13
> **関連**: [基本設計書](basic-design.md)

---

## 1. MCP Server 詳細設計

### 1.1 サーバー構成

`python
# src/saiten_mcp/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="saiten-mcp",
    version="1.0.0",
    description="Agents League @ TechConnect 採点エージェント用 MCP サーバー"
)
`

**Transport**: stdio (ローカル開発)
**依存パッケージ**: `mcp[cli]`, `pyyaml`, `pydantic`

### 1.2 ディレクトリ解決

すべてのファイルパスはプロジェクトルート基準で解決する:

`python
import pathlib
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
`

---

## 2. Tool 詳細設計

### 2.1 list_submissions

**目的**: GitHub Issue から提出物一覧を取得・パースする

`python
@mcp.tool()
async def list_submissions(
    track: str | None = None,  # "creative-apps" | "reasoning-agents" | "enterprise-agents" | None (全件)
    state: str = "all"         # "open" | "closed" | "all"
) -> list[dict]:
    """
    Agents League の提出物一覧を取得する。

    Returns:
        list of {
            "issue_number": int,
            "title": str,
            "track": str,          # "creative-apps" | "reasoning-agents" | "enterprise-agents" | "unknown"
            "project_name": str,
            "repo_url": str | None,
            "created_at": str,
            "has_demo": bool
        }
    """
`

**実装詳細**:
- `gh api repos/microsoft/agentsleague-techconnect/issues` を subprocess で実行
- Issue #10 以降を提出物として扱う（#1〜#9 はリポジトリ管理用）
- ラベルからトラック判定: `🎨 Creative Apps` → `creative-apps` 等
- ラベルがない場合は Issue 本文の `### Track` セクションからパース

**トラック判定ロジック**:

`python
TRACK_LABEL_MAP = {
    "Creative Apps": "creative-apps",
    "🎨 Creative Apps": "creative-apps",
    "Reasoning Agents": "reasoning-agents",
    "🧠 Reasoning Agents": "reasoning-agents",
    "Enterprise Agents": "enterprise-agents",
    "💼 Enterprise Agents": "enterprise-agents",
}

TRACK_BODY_MAP = {
    "Creative Apps - GitHub Copilot": "creative-apps",
    "Reasoning Agents - Microsoft Foundry": "reasoning-agents",
    "Enterprise Agents - M365 Agents Toolkit": "enterprise-agents",
}
`

**エラーハンドリング**:
- `gh` コマンド失敗 → 例外送出 (Fail Fast)
- JSON パース失敗 → 該当 Issue をスキップ、ログ出力

---

### 2.2 get_submission_detail

**目的**: 指定 Issue の詳細情報を構造化して返す

`python
@mcp.tool()
async def get_submission_detail(
    issue_number: int
) -> dict:
    """
    指定した Issue 番号の提出物詳細を取得する。

    Returns:
        {
            "issue_number": int,
            "title": str,
            "track": str,
            "project_name": str,
            "description": str,
            "repo_url": str | None,
            "readme_content": str | None,   # リポジトリの README.md
            "technologies": list[str],
            "technical_highlights": str,
            "has_demo": bool,
            "demo_description": str,
            "submission_checklist": dict,    # 各チェック項目の状態
            "team_members": str | None,
            "setup_summary": str
        }
    """
`

**Issue 本文パース**:

Issue テンプレートのセクションはすべて `### セクション名` で区切られている:

`python
SECTION_PARSERS = {
    "Track": parse_track,
    "Project Name": parse_text,
    "Microsoft Alias": parse_text,       # PII → 保存しない
    "GitHub Username": parse_text,       # PII → 保存しない  
    "Repository URL": parse_url,
    "Project Description": parse_text,
    "Demo Video or Screenshots": parse_demo,
    "Primary Programming Language": parse_text,
    "Key Technologies Used": parse_list,
    "Submission Requirements": parse_checklist,
    "Technical Highlights": parse_text,
    "Quick Setup Summary": parse_text,
    "Team Members (if any)": parse_text,
}
`

**README 取得**:

`python
async def fetch_readme(repo_url: str) -> str | None:
    """
    リポジトリ URL から README.md を取得。
    - GitHub URL をパースし owner/repo を抽出
    - gh api repos/{owner}/{repo}/readme --jq .content | base64 -d
    - 取得失敗時は None を返す (404, private repo 等)
    - 最大 10,000 文字に切り詰め (コンテキスト制限対策)
    """
`

**PII フィルタリング**:
- `Microsoft Alias` と `GitHub Username` は返却オブジェクトに含めない
- scores.json にも保存しない

---

### 2.3 get_scoring_rubric

**目的**: トラック別採点基準を返す

`python
@mcp.tool()
async def get_scoring_rubric(
    track: str  # "creative-apps" | "reasoning-agents" | "enterprise-agents"
) -> dict:
    """
    指定トラックの採点基準を返す。

    Returns:
        {
            "track": str,
            "track_display_name": str,
            "criteria": [
                {
                    "name": str,
                    "weight": float,        # 0.0〜1.0
                    "description": str,
                    "scoring_guide": {
                        "1-3": str,         # 低スコアの説明
                        "4-6": str,         # 中スコアの説明
                        "7-9": str,         # 高スコアの説明
                        "10": str           # 満点の説明
                    }
                }
            ],
            "total_weight": 1.0,
            "score_range": {"min": 1, "max": 10},
            "notes": str
        }
    """
`

**YAML ファイル形式** (`data/rubrics/creative-apps.yaml`):

`yaml
track: creative-apps
track_display_name: "🎨 Creative Apps"
notes: "Community Vote (10%) は自動採点対象外。残り 90% を按分して 100% とする。"

criteria:
  - name: "Accuracy & Relevance"
    weight: 0.222   # 20% / 90% ≈ 22.2%
    description: "提出物が課題要件を正確に満たしているか。GitHub Copilot の活用度。"
    scoring_guide:
      "1-3": "要件の半分以上を満たしていない。Copilot 活用が不明確。"
      "4-6": "基本要件は満たすが、一部不足。Copilot 活用は限定的。"
      "7-9": "全要件を満たし、Copilot を効果的に活用。MCP 統合あり。"
      "10":  "要件を超越。Copilot の革新的活用。複数 MCP 統合。"

  - name: "Reasoning & Multi-step Thinking"
    weight: 0.222
    description: "エージェントの推論能力。段階的思考の実装。"
    scoring_guide:
      "1-3": "単純な入出力のみ。推論ステップなし。"
      "4-6": "基本的な条件分岐あり。限定的な多段推論。"
      "7-9": "明確な推論チェーン。エラーハンドリングを含む多段処理。"
      "10":  "自己改善ループ。ReAct/CoT 等の高度な推論パターン実装。"

  - name: "Creativity & Originality"
    weight: 0.167   # 15% / 90% ≈ 16.7%
    description: "アイデアの独創性。既存ツールにない価値提案。"
    scoring_guide:
      "1-3": "既存ツールの単純なラッパー。独自性なし。"
      "4-6": "一部独自のアプローチ。既知の問題の新しい解法。"
      "7-9": "ユニークなコンセプト。明確な差別化要素。"
      "10":  "革新的。新しいカテゴリを創出するレベル。"

  - name: "UX & Presentation"
    weight: 0.167
    description: "ユーザー体験の質。デモ・ドキュメントの充実度。"
    scoring_guide:
      "1-3": "デモなし。README が不十分。使い方が不明。"
      "4-6": "スクリーンショットあり。基本的な README。"
      "7-9": "動画デモあり。詳細な README。セットアップ手順が明確。"
      "10":  "プロダクション品質の UX。洗練されたデモ。包括的ドキュメント。"

  - name: "Reliability & Safety"
    weight: 0.222
    description: "エラーハンドリング。セキュリティ考慮。堅牢性。"
    scoring_guide:
      "1-3": "エラーハンドリングなし。API キーがハードコード。"
      "4-6": "基本的なエラー処理。.env 使用だが不完全。"
      "7-9": "包括的エラーハンドリング。セキュリティベストプラクティス準拠。"
      "10":  "プロダクション品質。Rate limiting、リトライ、入力検証完備。"
`

---

### 2.4 save_scores

**目的**: 採点結果を永続化する

`python
@mcp.tool()
async def save_scores(
    scores: list[dict]
) -> dict:
    """
    採点結果を data/scores.json に保存する。
    既存スコアがある Issue は上書き (冪等性保証)。

    Input scores format:
        [
            {
                "issue_number": int,
                "project_name": str,
                "track": str,
                "criteria_scores": {
                    "Accuracy & Relevance": int,       # 1-10
                    "Reasoning & Multi-step Thinking": int,
                    ...
                },
                "weighted_total": float,    # 0-100
                "strengths": list[str],
                "improvements": list[str],
                "summary": str
            }
        ]

    Returns:
        {
            "saved_count": int,
            "updated_count": int,      # 既存上書き件数
            "total_in_store": int,
            "file_path": str
        }
    """
`

**scores.json スキーマ**:

`json
{
  "metadata": {
    "last_updated": "2026-02-13T12:00:00Z",
    "version": "1.0",
    "total_submissions": 42,
    "scored_count": 42
  },
  "scores": [
    {
      "issue_number": 46,
      "project_name": "PowerPoint Reviewer Agent",
      "track": "creative-apps",
      "criteria_scores": {
        "Accuracy & Relevance": 7,
        "Reasoning & Multi-step Thinking": 6,
        "Creativity & Originality": 7,
        "UX & Presentation": 6,
        "Reliability & Safety": 5
      },
      "weighted_total": 62.3,
      "strengths": ["GPT-4 による文脈理解", "自律的修正ループ"],
      "improvements": ["エラーハンドリングが不十分", "テストなし"],
      "summary": "PowerPoint の自動レビュー・修正という実用的なアプローチ...",
      "scored_at": "2026-02-13T12:00:00Z"
    }
  ]
}
`

**冪等性保証**:

`python
def merge_scores(existing: list[dict], new: list[dict]) -> list[dict]:
    """
    issue_number をキーとして既存スコアを上書き。
    新規 Issue は追加。削除はしない。
    """
    score_map = {s["issue_number"]: s for s in existing}
    for s in new:
        s["scored_at"] = datetime.utcnow().isoformat() + "Z"
        score_map[s["issue_number"]] = s
    return sorted(score_map.values(), key=lambda x: x["weighted_total"], reverse=True)
`

---

### 2.5 generate_ranking_report

**目的**: scores.json からランキング Markdown を生成する

`python
@mcp.tool()
async def generate_ranking_report(
    top_n: int = 10  # Top N 件を強調表示
) -> dict:
    """
    data/scores.json を読み込み reports/ranking.md を生成する。

    Returns:
        {
            "report_path": str,
            "total_scored": int,
            "top_n": int,
            "top_entries": [
                {"rank": 1, "project_name": str, "track": str, "score": float}
            ]
        }
    """
`

**出力 Markdown テンプレート**:

`markdown
# 🏆 Agents League @ TechConnect — 採点ランキング

> 自動生成: {timestamp}
> 採点済み: {scored_count} / {total_submissions} 件

---

## 🥇 Top {top_n}

| 順位 | Project | Track | 総合 | Acc | Rea | Cre | UX | Rel/Tech | Biz |
|------|---------|-------|------|-----|-----|-----|-----|----------|-----|
| 1 | {name} | {track_emoji} | {score} | {s1} | {s2} | {s3} | {s4} | {s5} | {s6} |
| ... |

---

## 🏅 トラック別 Top 3

### 🎨 Creative Apps
| 順位 | Project | 総合スコア |
| ... |

### 🧠 Reasoning Agents
| ... |

### 💼 Enterprise Agents
| ... |

---

## 📊 全提出物スコア一覧

| # | Issue | Project | Track | Score | 評価日 |
|---|-------|---------|-------|-------|--------|
| ... |

---

## 📋 個別評価サマリー

### #{issue_number}: {project_name}
- **トラック**: {track}
- **スコア**: {weighted_total}/100
- **強み**: {strengths}
- **改善点**: {improvements}
- **総評**: {summary}

(全件分)
`

---

## 3. データモデル (Pydantic)

`python
# src/saiten_mcp/models.py
from pydantic import BaseModel, Field
from datetime import datetime

class CriteriaScore(BaseModel):
    name: str
    score: int = Field(ge=1, le=10)
    weight: float = Field(ge=0.0, le=1.0)

class SubmissionScore(BaseModel):
    issue_number: int
    project_name: str
    track: str
    criteria_scores: dict[str, int]
    weighted_total: float = Field(ge=0.0, le=100.0)
    strengths: list[str]
    improvements: list[str]
    summary: str
    scored_at: datetime = Field(default_factory=datetime.utcnow)

class ScoreStore(BaseModel):
    metadata: dict
    scores: list[SubmissionScore]

class ScoringCriteria(BaseModel):
    name: str
    weight: float
    description: str
    scoring_guide: dict[str, str]

class Rubric(BaseModel):
    track: str
    track_display_name: str
    criteria: list[ScoringCriteria]
    notes: str = ""

class Submission(BaseModel):
    issue_number: int
    title: str
    track: str
    project_name: str
    repo_url: str | None = None
    created_at: str
    has_demo: bool = False

class SubmissionDetail(BaseModel):
    issue_number: int
    title: str
    track: str
    project_name: str
    description: str
    repo_url: str | None = None
    readme_content: str | None = None
    technologies: list[str] = []
    technical_highlights: str = ""
    has_demo: bool = False
    demo_description: str = ""
    submission_checklist: dict = {}
    team_members: str | None = None
    setup_summary: str = ""
`

---

## 4. Agent 設計

### 4.1 saiten.agent.md 構成

`yaml
---
name: saiten
description: "Agents League @ TechConnect の提出物を採点し、ランキングを生成する"
tools:
  - "saiten-mcp"        # カスタム MCP サーバーの全ツール
  - "read/readFile"
  - "edit/editFiles"
  - "execute/runInTerminal"
  - "todo"
---
`

### 4.2 エージェントのワークフロー

**全件採点フロー**:

`
1. [Gate] MCP サーバーの起動確認
   - list_submissions() を呼び出し、応答があることを確認
   - 失敗 → "MCP サーバーが起動していません" とエラー報告

2. [Step] 提出物一覧取得
   - list_submissions() で全件取得
   - トラック別に分類

3. [Step] 採点基準取得
   - 出現する各トラックについて get_scoring_rubric(track) を呼出
   - 基準を内部コンテキストに保持

4. [Loop] 各提出物の採点 (トラック別にグループ化)
   a. get_submission_detail(issue_number)
   b. 採点基準に照らして各項目を 1-10 でスコアリング
      - 判断根拠を strengths/improvements/summary に記録
   c. weighted_total を計算
   d. save_scores([result]) で保存
   e. todo list を更新して進捗表示
   [Gate] パース失敗 → スキップしてログ、次の件へ

5. [Step] ランキング生成
   - generate_ranking_report(top_n=10)
   - 生成されたファイルパスを報告

6. [Output] Top 10 サマリーをユーザーに表示
`

**個別再採点フロー**:

`
1. get_submission_detail(issue_number)
2. get_scoring_rubric(track) で該当トラックの基準取得
3. 採点実行
4. save_scores([result]) で上書き保存
5. generate_ranking_report() でランキング更新
6. 変動をユーザーに報告
`

### 4.3 プロンプト設計のポイント

| 項目 | 設計 |
|------|------|
| **採点の一貫性** | rubric の scoring_guide を毎回参照し、根拠を明記 |
| **バイアス回避** | Issue の提出順序に依存しない。トラック内で基準を統一 |
| **透明性** | 各スコアに対する justification を必ず記載 |
| **Fail Fast** | パース不可の Issue はスキップし、エラーリストに追加 |

---

## 5. .vscode/mcp.json 設定

`json
{
  "servers": {
    "saiten-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/src/saiten_mcp",
        "python",
        "-m",
        "saiten_mcp.server"
      ],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
`

---

## 6. pyproject.toml

`	oml
[project]
name = "saiten-mcp"
version = "1.0.0"
description = "MCP Server for Agents League scoring"
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]>=1.0.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
saiten-mcp = "saiten_mcp.server:main"
`

---

## 7. エラーハンドリング一覧

| エラー | 検出タイミング | 対応 |
|--------|---------------|------|
| gh CLI 未インストール | list_submissions 初回呼出 | 明確なエラーメッセージ + インストール手順 |
| GitHub API 認証失敗 | list_submissions | GITHUB_TOKEN 設定手順を案内 |
| Issue パース失敗 | get_submission_detail | 該当件スキップ、エラーリストに追加 |
| リポジトリ非公開 | README 取得 | readme_content = None、Issue 本文のみで採点 |
| YAML ファイル不在 | get_scoring_rubric | FileNotFoundError → 利用可能トラック一覧を返却 |
| scores.json 破損 | save_scores | バックアップ作成後に新規作成 |
| ディスク書込失敗 | save_scores / generate_ranking_report | 例外送出、ユーザーに報告 |

---

## 8. テスト方針

| テスト種別 | 対象 | 方法 |
|-----------|------|------|
| Unit | Issue パーサー | pytest + モック Issue データ |
| Unit | スコア計算 | pytest + 既知の入力→期待出力 |
| Integration | MCP Tool 呼出 | FastMCP テストクライアント |
| E2E | エージェント全体 | VS Code で手動実行 + スクリーンショット |

---

## 9. 実装優先順位

| Phase | 対象 | 完了条件 |
|-------|------|---------|
| **P1** | MCP Server (5 tools) + Agent | `@saiten 採点して` で動作 |
| **P2** | 採点基準 YAML 3 トラック分 | 全トラックの rubric 完成 |
| **P3** | ランキングレポート出力 | reports/ranking.md が正しく生成 |
| **P4** | (Optional) Azure Container Apps | Dockerfile + deploy.sh |
| **P5** | (Optional) README + デモ動画 | 提出用ドキュメント |
