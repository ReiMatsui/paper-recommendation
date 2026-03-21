"""週次・月次トレンド合成パイプライン。"""

from datetime import datetime, timedelta, timezone

from loguru import logger

from ..config.settings import Settings
from ..llm.base import BaseLLMClient
from ..processor.synthesizer import ResearchSynthesizer
from ..reporter.markdown_reporter import MarkdownReporter
from ..storage.models import Synthesis
from ..storage.sqlite_store import SQLiteStore


class SynthesisPipeline:
    """指定期間の論文データを横断分析し、トレンドレポートを生成するパイプライン。"""

    def __init__(
        self,
        settings: Settings,
        llm_client: BaseLLMClient,
        sqlite_store: SQLiteStore,
        reporter: MarkdownReporter,
    ) -> None:
        self._settings = settings
        self._synthesizer = ResearchSynthesizer(llm_client)
        self._llm_provider = llm_client.provider_name
        self._sqlite = sqlite_store
        self._reporter = reporter

    def run_weekly(self) -> None:
        """直近 7 日間の週次合成レポートを生成する。"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        logger.info(f"=== Weekly synthesis started | {start.date()} ~ {now.date()} ===")
        self._run(now, start, "weekly")

    def run_monthly(self) -> None:
        """直近 30 日間の月次合成レポートを生成する。"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=30)
        logger.info(f"=== Monthly synthesis started | {start.date()} ~ {now.date()} ===")
        self._run(now, start, "monthly")

    def _run(self, end: datetime, start: datetime, period_type: str) -> None:
        all_papers = self._sqlite.get_papers_in_range(start, end)
        logger.info(f"Total extracted papers in range: {len(all_papers)}")

        for topic in self._settings.get_topics():
            topic_papers = [p for p in all_papers if p.topic == topic]
            logger.info(f"  topic={topic!r} papers={len(topic_papers)}")

            if period_type == "weekly":
                text = self._synthesizer.synthesize_weekly(topic, topic_papers, start, end)
            else:
                text = self._synthesizer.synthesize_monthly(topic, topic_papers, start, end)

            if text is None:
                logger.warning(f"  Synthesis skipped | topic={topic!r}")
                continue

            synthesis = Synthesis(
                period_type=period_type,
                period_start=start,
                period_end=end,
                topic=topic,
                synthesis_text=text,
                paper_count=len(topic_papers),
                llm_provider=self._llm_provider,
            )
            self._sqlite.save_synthesis(synthesis)
            path = self._reporter.write_synthesis(synthesis)
            logger.info(f"  Report written | path={path}")

        logger.info(f"=== {period_type.capitalize()} synthesis finished ===")
