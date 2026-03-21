"""依存性注入コンテナ。

全コンポーネントの初期化と接続を一箇所で管理する。
main.py はこのモジュールを経由してパイプラインを取得するだけでよい。
"""

from .collector.arxiv_collector import ArxivCollector
from .config.settings import Settings
from .llm.factory import create_llm_client
from .pipeline.daily_pipeline import DailyPipeline
from .pipeline.synthesis_pipeline import SynthesisPipeline
from .reporter.markdown_reporter import MarkdownReporter
from .scheduler.job_scheduler import JobScheduler
from .storage.sqlite_store import SQLiteStore
from .storage.vector_store import VectorStore


def build_daily_pipeline(settings: Settings) -> DailyPipeline:
    """DailyPipeline に必要な全依存物を生成して注入する。"""
    return DailyPipeline(
        settings=settings,
        collector=ArxivCollector(settings),
        llm_client=create_llm_client(settings),
        sqlite_store=SQLiteStore(settings.get_db_path()),
        vector_store=VectorStore(settings.get_vector_db_path()),
        reporter=MarkdownReporter(settings.get_output_dir()),
    )


def build_synthesis_pipeline(settings: Settings) -> SynthesisPipeline:
    """SynthesisPipeline に必要な全依存物を生成して注入する。"""
    return SynthesisPipeline(
        settings=settings,
        llm_client=create_llm_client(settings),
        sqlite_store=SQLiteStore(settings.get_db_path()),
        reporter=MarkdownReporter(settings.get_output_dir()),
    )


def build_scheduler(settings: Settings) -> JobScheduler:
    """JobScheduler に必要な全依存物を生成して注入する。"""
    return JobScheduler(
        settings=settings,
        daily_pipeline=build_daily_pipeline(settings),
        synthesis_pipeline=build_synthesis_pipeline(settings),
    )
