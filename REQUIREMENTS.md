# 要件定義書: 研究アイデア創出エンジン

**バージョン**: 0.2.0
**最終更新**: 2026-03-23
**対象**: 個人利用・ローカル運用

---

## 1. システム概要

arXiv から研究論文を自動収集・LLM 解析し、トレンド把握と研究アイデアの自律的な創出を支援するシステム。
毎日メールで最新論文を受け取りつつ、ブラウザ UI から論文閲覧・検索・アイデア生成ができる。

---

## 2. アーキテクチャ

```
┌──────────────────────────────────────────────────┐
│          Streamlit UI (localhost:8501)            │
│  論文ブラウザ | 検索 | レポート | アイデア生成 ...  │
└────────────────────┬─────────────────────────────┘
                     │ import
┌────────────────────▼─────────────────────────────┐
│              Python Backend                       │
│  collector / extractor / synthesizer / ideas     │
└──────┬──────────────┬──────────────┬─────────────┘
       │              │              │
   SQLite          ChromaDB      Gemini API
  (papers,         (vector        (無料枠)
  ideas,           embeddings)
  feedback...)
```

**起動方法:**
```bash
# バックエンド（毎日自動: launchd）
uv run python main.py run

# フロントエンド（手動起動）
uv run streamlit run app.py
```

---

## 3. 技術スタック

| 層 | 技術 | 選定理由 |
|---|---|---|
| フロントエンド | Streamlit | Python完結・Markdown/グラフ表示が容易・個人用途に適切 |
| バックエンド | Python 3.13 | 既存資産の活用 |
| LLM | Gemini 1.5 Flash | 無料枠 (1,500 req/日) で十分 |
| メタデータDB | SQLite + SQLAlchemy | 軽量・ローカル・依存なし |
| ベクトルDB | ChromaDB | ローカル動作・追加費用なし |
| スケジューラ | macOS launchd | OS標準機能・軽量 |
| メール通知 | Gmail SMTP | 無料 |

**費用:**
- 通常運用: **無料**（Gemini 無料枠内: 日次40〜60リクエスト程度）
- アイデア生成・クロス分析を頻繁に使う場合: Gemini 無料枠を超える可能性あり
  → その場合のみ従量課金（$0.075/1M tokens 程度）

---

## 4. 機能要件

### 4.1 バックエンド（既存 + 追加）

| ID | 機能 | フェーズ | 状態 |
|---|---|---|---|
| B-01 | arXiv 論文収集（日次自動） | 既存 | ✅ 完了 |
| B-02 | LLM 構造化抽出（problem/method/claims/limitations/open_questions） | 既存 | ✅ 完了 |
| B-03 | SQLite + ChromaDB 保存 | 既存 | ✅ 完了 |
| B-04 | 日次トレンド分析（今日 vs 過去7日） | 既存 | ✅ 完了 |
| B-05 | 週次・月次合成レポート | 既存 | ✅ 完了 |
| B-06 | Gmail メール通知 | 既存 | ✅ 完了 |
| B-07 | ブートストラップ（過去N日一括収集） | 既存 | ✅ 完了 |
| B-08 | 重要度スコアリング（ヒューリスティック） | Phase 1 | 🔲 未着手 |
| B-09 | クロストピック合成 | Phase 1 | 🔲 未着手 |
| B-10 | 研究アイデア生成 | Phase 2 | 🔲 未着手 |
| B-11 | 新規性チェック（ベクトル検索） | Phase 2 | 🔲 未着手 |
| B-12 | フィードバック記録・集計 | Phase 3 | 🔲 未着手 |

### 4.2 フロントエンド UI

| ID | 画面 | 機能 | フェーズ |
|---|---|---|---|
| U-01 | 論文ブラウザ | 一覧・フィルタ（日付/トピック）・カード展開 | UI |
| U-02 | 論文ブラウザ | 重要度スコア表示・arXiv リンク | Phase 1 |
| U-03 | 検索 | セマンティック検索・距離スコア表示 | UI |
| U-04 | レポート | 日次/週次/月次/Bootstrap の Markdown 閲覧 | UI |
| U-05 | レポート | 今すぐ生成ボタン | UI |
| U-06 | クロストピック分析 | 複数トピック選択 → LLM 分析 → 結果表示 | Phase 1 |
| U-07 | 研究アイデア生成 | アイデア生成・新規性チェック・保存 | Phase 2 |
| U-08 | フィードバック管理 | 興味あり/なし記録・傾向集計 | Phase 3 |

---

## 5. データモデル

### 既存テーブル

**`papers`**
```
id, arxiv_id (unique), title, abstract, authors (JSON),
published_at, collected_at, topic, pdf_url,
problem, method, claims, limitations, open_questions,
llm_provider, extracted_at
```

**`syntheses`**
```
id, period_type, period_start, period_end, topic,
synthesis_text, paper_count, llm_provider, generated_at
```

### 追加テーブル（Phase 1〜3）

**`paper_scores`** (Phase 1)
```
id, arxiv_id (unique), importance FLOAT,
score_method TEXT, scored_at DATETIME
```

**`cross_syntheses`** (Phase 1)
```
id, topics TEXT (JSON), period_start, period_end,
synthesis_text, paper_count, generated_at
```

**`ideas`** (Phase 2)
```
id, title, description, source_arxiv_ids (JSON),
novelty_score FLOAT, is_saved BOOLEAN, created_at
```

**`feedback`** (Phase 3)
```
id, arxiv_id, rating TEXT (interested/not_interested),
memo TEXT, created_at
```

---

## 6. 画面仕様

### ホーム (`app.py`)
- 収集論文数・抽出済み論文数・直近7日の収集数をメトリクス表示
- トピック別論文数の棒グラフ
- 最新5件の論文タイトルをリスト表示

### 論文ブラウザ (`pages/1_papers.py`)
- フィルター: 日付レンジ / トピック複数選択 / 抽出済みのみ
- 論文カード: タイトル / トピックバッジ / 著者 / 公開日
- expander 展開: problem / method / claims / limitations / open_questions
- フッター: arXiv PDF リンク / 興味あり・なしボタン（Phase 3）

### 検索 (`pages/2_search.py`)
- クエリ入力 + 件数スライダー（1〜20）
- 結果: タイトル / 類似度スコア / 論文詳細 expander

### レポート (`pages/3_reports.py`)
- タブ: 日次 / 週次 / 月次 / Bootstrap
- 日付セレクトボックス → Markdown レンダリング
- ダウンロードボタン

### クロストピック分析 (`pages/4_cross_topic.py`)  ← Phase 1
- トピック複数選択 + 期間スライダー
- 生成結果を DB キャッシュ（同一条件では再生成しない）

### 研究アイデア生成 (`pages/5_ideas.py`)  ← Phase 2
- 関心テーマ入力 + 期間選択
- 生成されたアイデアカード + 新規性スコア + ソース論文リンク
- 保存・削除操作

### フィードバック管理 (`pages/6_feedback.py`)  ← Phase 3
- 評価済み論文一覧
- 興味あり論文のトピック傾向グラフ

---

## 7. 非機能要件

| 項目 | 要件 |
|---|---|
| 動作環境 | macOS ローカル（localhost:8501） |
| 認証 | 不要（個人用） |
| レスポンス | UI 操作は 3 秒以内（LLM 生成を除く） |
| LLM コスト | Gemini 無料枠（1,500 req/日）内で通常運用を完結させる |
| データ保存 | ローカルファイル（data/ ディレクトリ） |
| バックアップ | git push で GitHub にコード管理（DB は対象外） |

---

## 8. 実装順序

```
Step 1: Streamlit 基本UI（論文ブラウザ・検索・レポート）
Step 2: 重要度スコアリング（ヒューリスティック）
Step 3: クロストピック合成
Step 4: 研究アイデア生成
Step 5: フィードバックループ
```
