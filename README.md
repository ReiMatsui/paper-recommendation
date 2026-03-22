# RAG Paper Recommend

arXiv から研究論文を自動収集し、LLM で構造化・分析してMarkdownレポートを生成するシステムです。
RAG（Retrieval-Augmented Generation）を活用した類似論文検索にも対応しています。

## 機能

- **自動収集**: arXiv から指定トピックの最新論文を毎日取得
- **LLM 解析**: 論文の要点・手法・貢献をLLMで構造化抽出
- **レポート生成**: 日次・週次・月次のMarkdownレポートを自動生成
- **類似論文検索**: ベクトルDBを使ったセマンティック検索
- **スケジューラ**: 毎日指定時刻に自動実行

## 対応LLMプロバイダー

| プロバイダー | モデル（デフォルト） | 備考 |
|---|---|---|
| Gemini (Google) | gemini-1.5-flash | **デフォルト**・無料枠あり |
| Claude (Anthropic) | claude-haiku-4-5 | 従量課金 |
| OpenAI | gpt-4o-mini | 従量課金 |

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、APIキーを設定します。

```bash
cp .env.example .env
```

```env
# 使用するLLMプロバイダーを選択 (gemini / claude / openai)
LLM_PROVIDER=gemini

# 選択したプロバイダーのAPIキーを設定
GOOGLE_API_KEY=your_google_api_key_here

# 収集するトピック（カンマ区切り）
ARXIV_TOPICS=RAG,retrieval augmented generation

# 毎日の実行時刻（JST）
DAILY_SCHEDULE_TIME=09:00
```

## 使い方

### 今すぐ実行

```bash
# 日次レポートを生成
uv run python main.py run

# 日次 + 週次レポートを生成
uv run python main.py run --weekly

# 日次 + 月次レポートを生成
uv run python main.py run --monthly
```

### スケジューラ常駐起動

```bash
# 毎日 DAILY_SCHEDULE_TIME に自動実行
uv run python main.py schedule
```

### 類似論文検索

```bash
uv run python main.py search "RAG with graph neural networks"
```

### レポート再生成

```bash
# 今日のレポートを再生成
uv run python main.py report

# 指定日のレポートを再生成
uv run python main.py report --date 2026-03-17
```

## ディレクトリ構成

```
.
├── main.py                         # CLIエントリーポイント
├── src/rag_paper_recommend/
│   ├── collector/                  # arXiv論文収集
│   ├── config/                     # 設定管理
│   ├── llm/                        # LLMクライアント（Gemini/Claude/OpenAI）
│   ├── pipeline/                   # 日次・合成パイプライン
│   ├── processor/                  # LLMによる構造化抽出
│   ├── reporter/                   # Markdownレポート生成
│   ├── scheduler/                  # スケジューラ
│   └── storage/                    # SQLite + ChromaDB
├── data/
│   ├── db/                         # SQLiteデータベース
│   └── vector/                     # ChromaDBベクトルストア
└── output/reports/                 # 生成されたレポート（日付別）
```

## 出力例

レポートは `output/reports/YYYY-MM-DD/daily_report.md` に保存されます。

```markdown
# 論文収集レポート 2026年03月17日

収集論文数: 20 件

---
## 論文タイトル

- **著者**: ...
- **公開日**: 2026-03-16
- **概要**: ...
- **手法**: ...
- **貢献**: ...
```
