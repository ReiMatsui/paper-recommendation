"""ブートストラップパイプライン: 初回の大量論文収集・分析・レポート生成。

通常の日次パイプラインとは異なり、過去 N 日分を一括収集して
フィールド概観レポートを生成する。
"""

from datetime import datetime, timezone

from loguru import logger

from ..collector.arxiv_collector import ArxivCollector
from ..config.settings import Settings
from ..llm.base import BaseLLMClient
from ..notifier.email_notifier import EmailNotifier
from ..processor.bootstrap_synthesizer import BootstrapSynthesizer
from ..processor.extractor import PaperExtractor
from ..reporter.markdown_reporter import MarkdownReporter
from ..storage.models import Paper
from ..storage.sqlite_store import SQLiteStore
from ..storage.vector_store import VectorStore

# ブートストラップ時のトピックごとの最大収集件数
BOOTSTRAP_MAX_RESULTS = 500


class BootstrapPipeline:
    """初回セットアップ用の大量収集・分析パイプライン。"""

    def __init__(
        self,
        settings: Settings,
        llm_client: BaseLLMClient,
        sqlite_store: SQLiteStore,
        vector_store: VectorStore,
        reporter: MarkdownReporter,
        notifier: EmailNotifier,
    ) -> None:
        self._settings = settings
        self._collector = ArxivCollector(settings)
        self._extractor = PaperExtractor(llm_client)
        self._synthesizer = BootstrapSynthesizer(llm_client)
        self._llm_provider = llm_client.provider_name
        self._sqlite = sqlite_store
        self._vector = vector_store
        self._reporter = reporter
        self._notifier = notifier

    def run(self, days: int = 180) -> None:
        """過去 days 日分の論文を収集・分析してフィールド概観レポートを生成する。"""
        now = datetime.now(timezone.utc)
        logger.info(f"=== Bootstrap pipeline started | days={days} ===")

        # 1. 大量収集（max_results を一時的に拡張）
        original_max = self._collector._max_results
        self._collector._max_results = BOOTSTRAP_MAX_RESULTS
        try:
            raw_papers = self._collector.fetch(
                topics=self._settings.get_topics(),
                days_back=days,
            )
        finally:
            self._collector._max_results = original_max

        # 2. 重複排除
        new_papers = [p for p in raw_papers if not self._sqlite.exists(p.arxiv_id)]
        logger.info(
            f"Collected={len(raw_papers)} | New={len(new_papers)} | "
            f"Skipped(dup)={len(raw_papers) - len(new_papers)}"
        )

        # 3. 保存 + LLM抽出
        processed: list[Paper] = []
        for i, raw in enumerate(new_papers, 1):
            try:
                paper = Paper(
                    arxiv_id=raw.arxiv_id,
                    title=raw.title,
                    abstract=raw.abstract,
                    authors=raw.authors,
                    published_at=raw.published_at,
                    pdf_url=raw.pdf_url,
                    topic=raw.topic,
                )
                self._sqlite.save_paper(paper)

                extraction = self._extractor.extract(raw)
                if extraction:
                    self._sqlite.update_extraction(
                        raw.arxiv_id, extraction, self._llm_provider
                    )
                    paper.problem = extraction.get("problem")
                    paper.method = extraction.get("method")
                    paper.claims = extraction.get("claims")
                    paper.limitations = extraction.get("limitations")
                    paper.open_questions = extraction.get("open_questions")

                self._vector.upsert(
                    arxiv_id=raw.arxiv_id,
                    text=f"{raw.title}\n{raw.abstract}",
                    metadata={
                        "title": raw.title,
                        "topic": raw.topic,
                        "published_at": raw.published_at.isoformat(),
                    },
                )
                processed.append(paper)

                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{len(new_papers)}")

            except Exception as e:
                logger.error(f"  [FAIL] {raw.arxiv_id} | {e}")
                continue

        logger.info(f"Extraction complete | {len(processed)}/{len(new_papers)} papers")

        # 4. トピックごとにブートストラップ合成レポートを生成
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        start_dt = start_dt - timedelta(days=days)

        for topic in self._settings.get_topics():
            topic_papers = [p for p in processed if p.topic == topic]
            logger.info(f"Synthesizing | topic={topic!r} papers={len(topic_papers)}")

            if not topic_papers:
                logger.warning(f"No papers for topic={topic!r}, skipping")
                continue

            synthesis_text = self._synthesizer.synthesize(
                topic=topic,
                papers=topic_papers,
                start=start_dt,
                end=now,
                days=days,
            )

            if synthesis_text is None:
                logger.warning(f"Synthesis failed | topic={topic!r}")
                continue

            report_path = self._reporter.write_bootstrap(
                topic=topic,
                days=days,
                date=now,
                paper_count=len(topic_papers),
                content=synthesis_text,
            )
            logger.info(f"Bootstrap report written | path={report_path}")

            # メール送信
            self._notifier.send_bootstrap_report(topic, days, report_path, len(topic_papers))

        logger.info("=== Bootstrap pipeline finished ===")
