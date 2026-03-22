"""日次パイプライン: 収集 → 構造化抽出 → 保存 → 日次レポート生成。"""

from datetime import datetime, timezone

from loguru import logger

from ..collector.base import BaseCollector
from ..config.settings import Settings
from ..llm.base import BaseLLMClient
from ..notifier.email_notifier import EmailNotifier
from ..processor.extractor import PaperExtractor
from ..reporter.markdown_reporter import MarkdownReporter
from ..storage.models import Paper
from ..storage.sqlite_store import SQLiteStore
from ..storage.vector_store import VectorStore


class DailyPipeline:
    """1 日分の論文収集・処理・保存を一貫して実行するパイプライン。

    エラーが発生した論文はスキップしてログに記録する設計のため、
    1 件の失敗でパイプライン全体が停止しない。
    """

    def __init__(
        self,
        settings: Settings,
        collector: BaseCollector,
        llm_client: BaseLLMClient,
        sqlite_store: SQLiteStore,
        vector_store: VectorStore,
        reporter: MarkdownReporter,
        notifier: EmailNotifier,
    ) -> None:
        self._settings = settings
        self._collector = collector
        self._extractor = PaperExtractor(llm_client)
        self._llm_provider = llm_client.provider_name
        self._sqlite = sqlite_store
        self._vector = vector_store
        self._reporter = reporter
        self._notifier = notifier

    def run(self) -> None:
        now = datetime.now(timezone.utc)
        logger.info(f"=== Daily pipeline started | {now.strftime('%Y-%m-%d %H:%M UTC')} ===")

        # 1. 論文収集
        raw_papers = self._collector.fetch(
            topics=self._settings.get_topics(),
            days_back=self._settings.arxiv_days_back,
        )

        # 2. 重複排除（既存 DB に登録済みのものを除外）
        new_papers = [p for p in raw_papers if not self._sqlite.exists(p.arxiv_id)]
        logger.info(
            f"Collected={len(raw_papers)} | New={len(new_papers)} | "
            f"Skipped(dup)={len(raw_papers) - len(new_papers)}"
        )

        # 3. 各論文を処理・保存
        processed: list[Paper] = []
        for raw in new_papers:
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

                # LLM による構造化抽出
                extraction = self._extractor.extract(raw)
                if extraction:
                    self._sqlite.update_extraction(
                        raw.arxiv_id, extraction, self._llm_provider
                    )
                    # レポート生成用にインメモリのオブジェクトにも反映
                    paper.problem = extraction.get("problem")
                    paper.method = extraction.get("method")
                    paper.claims = extraction.get("claims")
                    paper.limitations = extraction.get("limitations")
                    paper.open_questions = extraction.get("open_questions")
                else:
                    logger.warning(f"Extraction skipped | arxiv_id={raw.arxiv_id}")

                # ベクトルストアへの登録
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
                logger.info(f"  [OK] {raw.arxiv_id} | {raw.title[:60]}...")

            except Exception as e:
                logger.error(f"  [FAIL] {raw.arxiv_id} | {e}")
                continue

        # 4. 日次レポート生成
        report_path = self._reporter.write_daily(now, processed)
        logger.info(f"Daily report written | path={report_path}")

        # 5. メール通知
        self._notifier.send_daily_report(now, report_path, len(processed))

        logger.info(
            f"=== Daily pipeline finished | processed={len(processed)}/{len(new_papers)} ==="
        )
