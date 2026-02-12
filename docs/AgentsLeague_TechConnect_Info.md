# Agents League @ TechConnect — イベント情報まとめ

> **リポジトリ**: <https://github.com/microsoft/agentsleague-techconnect>
> **提出期限**: 2026年2月13日 (金) 11:59 PM PT
> **形式**: 2時間の対面 AI エージェント ハッカソン（Microsoft 社員向け@TechConnect）

---

## 🏟️ 概要

- **e-Sports スタイル**の対面 AI エージェント ハッカソン
- GitHub Copilot / Microsoft Foundry / M365 Agents Toolkit を使って AI エージェントを構築
- スキルレベル不問（初心者〜エキスパートまで参加可能）

---

## ⏰ タイムスケジュール

| 時間       | 内容                       |
| ---------- | -------------------------- |
| 10 分      | Welcome & トラック概要説明 |
| **100 分** | **エージェント構築**       |
| 10 分      | ラップアップ               |

> 審査はイベント後に行われ、受賞者は後日発表

---

## ✅ 事前準備 (Prerequisites)

| 項目            | 詳細                                                            |
| --------------- | --------------------------------------------------------------- |
| 💻 ラップトップ | 持参（BYOD）                                                    |
| 🔑 テナント     | M365 Copilot ライセンス、Microsoft Azure、GitHub Copilot が必要 |
| 🛠️ VS Code      | インストール済みであること                                      |
| 🥳 やる気       | 新しいものを作る開発者マインドセット                            |

---

## 🏁 チャレンジ トラック（3 つから1つ選択）

### Track 1: 🎨 Creative Apps — GitHub Copilot

**概要**: GitHub Copilot + VS Code で革新的なクリエイティブアプリを構築

**必須要件**:

1. **GitHub Copilot の活用** — 開発中の Copilot 活用を実証
2. **クリエイティブなアプリ** — ユニークで価値あるアプリケーション
3. **MCP (Model Context Protocol) 統合** — 外部データソースとの接続

**推奨ツール**:

- [Copilot CLI SDK](https://github.com/github/copilot-sdk)
- [WorkIQ MCP](https://github.com/microsoft/work-iq-mcp)
- GitHub MCP / Microsoft Learn MCP

**プロジェクトアイデア例**:

- 📊 BI ダッシュボード（会議インサイト、Sales Pipeline 分析）
- 🤝 チームコラボレーション（Smart Standup Bot、ナレッジベースビルダー）
- 📝 ドキュメントワークフロー（提案書ジェネレーター、リリースノート自動化）
- 📅 リソース管理（キャパシティプランニング、ベンダー管理）

**アプリ形式**: Web / CLI / モバイル / デスクトップ / ゲーム / VR/AR すべて可

**評価基準**:
| 基準 | 割合 |
|------|------|
| Accuracy & Relevance | 20% |
| Reasoning & Multi-step Thinking | 20% |
| Creativity & Originality | 15% |
| UX & Presentation | 15% |
| Reliability & Safety | 20% |
| Community Vote (Discord) | 10% |

---

### Track 2: 🧠 Reasoning Agents — Microsoft Foundry

**概要**: Microsoft Foundry でマルチステップ推論を行うインテリジェントエージェント構築

**シナリオ**: ソーシャルメディアコンテンツを作成する**コミュニケーションチーム支援 AI エージェント**を構築。業界やブランドを自由に選択。

**Prerequisites** (Track固有):
| 項目 | 対象 |
|------|------|
| ☁️ Azure Subscription | GPT モデルクォータ 100k–300k TPM |
| 🐍 Python 3.10+ | Code-First の場合 |
| ⌨️ Azure CLI | SDK 使用時の認証 |

**Quick Start (2つのオプション)**:

1. **Foundry Portal** — [ai.azure.com](https://ai.azure.com/) → プロジェクト作成 → モデルデプロイ → Playground
2. **Foundry SDK (Python)** — `pip install azure-ai-projects azure-identity`

**推奨モデル**: GPT-5.1, GPT-5.2, Claude Opus 4.5 等の推論特化モデル

**プロジェクトマイルストーン**:

1. Microsoft Foundry 環境セットアップ＆モデルデプロイ
2. エージェント作成（指示設定、推論パターン実装）
3. グラウンディング知識追加（データソース統合）
4. 外部ツール連携（MCP サーバー、API）

**推論パターン**:

- **Chain-of-Thought**: ステップバイステップで思考
- **ReAct**: 推論 + アクションの組み合わせ
- **Self-Reflection**: 自己チェック＆修正

**ボーナス**: 評価メトリクス設定、モニタリング、安全対策、マルチエージェント構成

---

### Track 3: 💼 Enterprise Agents — M365 Agents Toolkit

**概要**: Microsoft 365 Copilot を拡張するエンタープライズ向けエージェント構築

**開発アプローチ（3つから選択）**:

1. **Declarative Agents (DA)** — ATK + VS Code でノーコード/ローコード宣言的構成
2. **Custom Engine Agents (CEA)** — ATK + VS Code/Visual Studio でフルコード制御（C#/.NET）
3. **Copilot Studio** — ローコード/ノーコードのビジュアルデザイナー

**Prerequisites** (Track固有):
| 項目 | 詳細 |
|------|------|
| 🎫 M365 Copilot License | エージェントテスト・デプロイに必要 |
| 🏢 Sideloading 有効テナント | カスタムアプリのサイドロード |
| ☁️ Azure Subscription | CEA 用リソース作成 |

**シナリオ例**:

- 🏢 HR エージェント（ポリシー案内、休暇申請、オンボーディング）
- 🔬 R&D エージェント（文献検索、IP 管理、プロジェクト追跡）
- 📦 サプライチェーン管理エージェント
- 💰 Finance & Accounting エージェント
- 🖥️ IT ヘルプデスクエージェント
- ⚖️ Legal & Compliance エージェント
- 📈 Sales Enablement エージェント
- 🏥 保険クレーム処理エージェント

**評価基準**:
| 基準 | 配点 | 割合 |
|------|------|------|
| 🔧 Technical Implementation | 33点 | 33% |
| 💼 Business Value | 33点 | 33% |
| 💡 Innovation & Creativity | 34点 | 34% |

**Technical Implementation の内訳**:
| 項目 | 点数 | 必須/任意 |
|------|------|-----------|
| M365 Copilot Chat Agent | Pass/Fail | **必須** |
| External MCP Server (Read/Write) | 最大 8点 | 任意（推奨） |
| OAuth Security | 最大 5点 | 任意 |
| Adaptive Cards | 最大 5点 | 任意 |
| Connected Agents | 最大 15点 | 任意（高評価） |

---

## 📝 提出方法

1. **トラック選択** → starter-kits でセットアップガイド確認
2. **100分で構築** — スクショ or デモ動画を含む
3. **Issue で提出** — [Project Submission Template](https://github.com/microsoft/agentsleague-techconnect/issues/new?template=project.yml) を使用
4. **期限**: **2026年2月13日 11:59 PM PT**

**提出前チェックリスト**:

- ❌ API キー、パスワード、クレデンシャルなし
- ❌ 顧客データ、PII なし
- ❌ Microsoft Confidential 情報なし
- ✅ リポジトリは Public で README を含む
- ✅ Microsoft alias を提出時に記入
- ✅ [DISCLAIMER.md](https://github.com/microsoft/agentsleague-techconnect/blob/main/DISCLAIMER.md) と [CODE_OF_CONDUCT.md](https://github.com/microsoft/agentsleague-techconnect/blob/main/CODE_OF_CONDUCT.md) を確認済み

---

## 🏆 審査基準（全体共通）

| 基準                            | 割合 |
| ------------------------------- | ---- |
| Accuracy & Relevance            | 25%  |
| Reasoning & Multi-step Thinking | 25%  |
| Creativity & Originality        | 20%  |
| User Experience & Presentation  | 15%  |
| Technical Implementation        | 15%  |

---

## 🏅 賞・表彰

### Track Winners

| 賞                        | 内容                             |
| ------------------------- | -------------------------------- |
| 🎨 Creative Apps Champion | Creative Apps トラック最優秀     |
| 🧠 Reasoning Master       | Reasoning Agents トラック最優秀  |
| 💼 Enterprise MVP         | Enterprise Agents トラック最優秀 |

### In-room Awards（会場内賞）

| 賞                             | 内容                                         |
| ------------------------------ | -------------------------------------------- |
| 🚀 Speed Demon                 | 最速で動くプロジェクトを提出                 |
| 🔧 Hackiest Hack               | なんとか動く最もスクラッピーなソリューション |
| 🐛 Bug Whisperer               | 40分デバッグ…原因はカンマ1つ                 |
| 🧱 It Worked Yesterday Award   | 偉い人が来た瞬間にデモが壊れた               |
| 🧙 Used Magic                  | 本人含め誰も仕組みを理解していない           |
| 🔌 Turning it Off and On Award | オフ→オンで全部解決                          |
| 🎨 Fake It Till You Make It    | UI は最高、バックエンドは存在しない          |
| 📢 Hype Machine                | コーディングより語りの方が多い               |
| 🎪 Last Minute Legend          | 最後の1時間で全部やった                      |

### 全参加者

- 🎖️ **Digital Badge** — プロジェクト提出者全員に配布
- Agents League Arena で戦った永遠の栄光

---

## 💬 コミュニティ & サポート

| リソース                          | リンク                                 |
| --------------------------------- | -------------------------------------- |
| Agents League Discord             | <https://aka.ms/agentsleague/discord>  |
| Microsoft Foundry Discord         | <https://discord.gg/nTYy5BXMWG>        |
| Microsoft Foundry Developer Forum | <https://aka.ms/foundry/forum>         |
| 会場内ヘルプ                      | 手を挙げてローミングエキスパートに質問 |

---

## 📚 主要リンク集

| リソース                      | URL                                                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| メインリポジトリ              | <https://github.com/microsoft/agentsleague-techconnect>                                                                              |
| Creative Apps Starter Kit     | [starter-kits/1-creative-apps](https://github.com/microsoft/agentsleague-techconnect/tree/main/starter-kits/1-creative-apps)         |
| Reasoning Agents Starter Kit  | [starter-kits/2-reasoning-agents](https://github.com/microsoft/agentsleague-techconnect/tree/main/starter-kits/2-reasoning-agents)   |
| Enterprise Agents Starter Kit | [starter-kits/3-enterprise-agents](https://github.com/microsoft/agentsleague-techconnect/tree/main/starter-kits/3-enterprise-agents) |
| プロジェクト提出              | [Issue Template](https://github.com/microsoft/agentsleague-techconnect/issues/new?template=project.yml)                              |
| VS Code セットアップ          | <https://code.visualstudio.com/docs/setup/setup-overview>                                                                            |
| GitHub Copilot                | <https://code.visualstudio.com/docs/copilot/overview>                                                                                |
| Microsoft Foundry             | <https://ai.azure.com/>                                                                                                              |
| Copilot Dev Camp              | <https://aka.ms/copilotdevcamp>                                                                                                      |
| Agent Academy                 | <https://aka.ms/agentacademy>                                                                                                        |
| Copilot Studio                | <https://copilotstudio.microsoft.com/>                                                                                               |
| MCP in VS Code                | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers>                                                                        |

---

## 🎯 勝利のための戦略ヒント

1. **Real Problem を解決する** — 日々のペインポイントに焦点
2. **深さ > 広さ** — 1つのことを exceptionally well にやる
3. **Show, Don't Tell** — デモで価値を体験させる
4. **MCP 統合を入れる** — 特に Read/Write ができると高評価
5. **プロダクション品質を意識** — セキュリティ、スケーラビリティ
6. **スクリーンショット / デモ動画を必ず含める**

---

## ❓ FAQ

- **Vibe-coding OK?** → ✅ GitHub Copilot 等の AI コーディングアシスタント使用を推奨
- **OSS ライブラリ使用?** → ✅ OK
- **商用/有料ライブラリ?** → ❌ NG（無料で利用可能なツールのみ）
- **既存プロジェクトの提出?** → ❌ NG（ハッカソン用のオリジナル作品のみ）
- **コード必須?** → Track による（Foundry は Portal のみでも可、Enterprise は Copilot Studio でノーコードも可）
- **MCP 統合は必須?** → Creative Apps は必須、Enterprise は任意だが高得点要素

---

_最終更新: 2026-02-12 | Source: [microsoft/agentsleague-techconnect](https://github.com/microsoft/agentsleague-techconnect)_
