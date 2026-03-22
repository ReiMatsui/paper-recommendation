"""RAG Paper Recommend - CLI エントリーポイント。

使い方:
    uv run python main.py bootstrap         # 初回セットアップ（過去180日分を収集・分析）
    uv run python main.py bootstrap --days 90  # 期間を指定
    uv run python main.py run               # 今すぐ 1 回実行
    uv run python main.py run --weekly      # 実行後に週次合成も実行
    uv run python main.py schedule          # スケジューラ常駐起動
    uv run python main.py search "クエリ"   # 類似論文検索
    uv run python main.py report            # 今日のレポート再生成
    uv run python main.py report --date 2026-03-17
"""

from datetime import datetime

import typer

app = typer.Typer(
    name="rag-paper-recommend",
    help="研究論文の自動収集・トレンド分析システム",
    add_completion=False,
)


@app.command()
def bootstrap(
    days: int = typer.Option(180, "--days", help="何日前まで遡って収集するか"),
) -> None:
    """初回セットアップ: 過去 N 日分の論文を一括収集してフィールド概観レポートを生成する。"""
    from rag_paper_recommend.config.settings import settings
    from rag_paper_recommend.container import build_bootstrap_pipeline

    typer.echo(f"Starting bootstrap: collecting papers from the past {days} days...")
    typer.echo("This may take a while (30-60 minutes for 180 days). Please wait.")
    build_bootstrap_pipeline(settings).run(days=days)


@app.command()
def run(
    weekly: bool = typer.Option(False, "--weekly", help="実行後に週次合成レポートも生成する"),
    monthly: bool = typer.Option(False, "--monthly", help="実行後に月次合成レポートも生成する"),
) -> None:
    """論文収集・抽出パイプラインを即時実行する。"""
    from rag_paper_recommend.config.settings import settings
    from rag_paper_recommend.container import (
        build_daily_pipeline,
        build_synthesis_pipeline,
    )

    build_daily_pipeline(settings).run()

    if weekly or monthly:
        synthesis = build_synthesis_pipeline(settings)
        if weekly:
            synthesis.run_weekly()
        if monthly:
            synthesis.run_monthly()


@app.command()
def schedule() -> None:
    """スケジューラを起動して毎日自動実行する（Ctrl+C で停止）。"""
    from rag_paper_recommend.config.settings import settings
    from rag_paper_recommend.container import build_scheduler

    build_scheduler(settings).start()


@app.command()
def search(
    query: str = typer.Argument(..., help="検索クエリ（日本語・英語どちらも可）"),
    n: int = typer.Option(5, "--n", help="返す件数"),
) -> None:
    """蓄積した論文から意味的に類似した論文を検索する。"""
    from rag_paper_recommend.config.settings import settings
    from rag_paper_recommend.storage.vector_store import VectorStore

    store = VectorStore(settings.get_vector_db_path())
    results = store.search_similar(query, n_results=n)

    if not results:
        typer.echo("No results found. Have you run the pipeline yet?")
        raise typer.Exit(1)

    typer.echo(f"\nSearch results for: {query!r}\n")
    for i, r in enumerate(results, 1):
        title = r["metadata"].get("title", "Unknown")
        topic = r["metadata"].get("topic", "")
        typer.echo(f"[{i}] {title}")
        typer.echo(f"    arXiv: {r['arxiv_id']} | topic: {topic} | distance: {r['distance']:.4f}")


@app.command()
def report(
    date: str = typer.Option(
        default="",
        help="レポートを再生成する日付（YYYY-MM-DD）。省略時は今日。",
    ),
) -> None:
    """指定した日の日次レポートを再生成する。"""
    from rag_paper_recommend.config.settings import settings
    from rag_paper_recommend.reporter.markdown_reporter import MarkdownReporter
    from rag_paper_recommend.storage.sqlite_store import SQLiteStore

    target = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    store = SQLiteStore(settings.get_db_path())
    reporter = MarkdownReporter(settings.get_output_dir())

    papers = store.get_papers_by_date(target)
    if not papers:
        typer.echo(f"No papers found for {target.strftime('%Y-%m-%d')}.")
        raise typer.Exit(1)

    path = reporter.write_daily(target, papers)
    typer.echo(f"Report written to: {path}")


if __name__ == "__main__":
    app()
