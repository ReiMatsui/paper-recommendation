"""arXiv API を使った論文収集実装。"""

from datetime import datetime, timedelta, timezone

import arxiv
from loguru import logger

from ..config.settings import Settings
from .base import BaseCollector, PaperRaw


class ArxivCollector(BaseCollector):
    """arXiv API から論文を収集するコレクター。

    同一論文が複数トピックにマッチする場合、最初にマッチしたトピックで記録する。
    """

    def __init__(self, settings: Settings, delay_seconds: float = 3.0) -> None:
        self._max_results = settings.arxiv_max_results_per_topic
        self._client = arxiv.Client(
            page_size=100,
            delay_seconds=delay_seconds,
            num_retries=5,
        )

    def fetch(self, topics: list[str], days_back: int = 1) -> list[PaperRaw]:
        """arXiv API から複数トピックの論文を収集する。

        Args:
            topics: 検索トピックのリスト。
            days_back: 何日前までの論文を対象にするか。

        Returns:
            収集した論文リスト。トピックをまたいだ重複は除外済み。
        """
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        seen_ids: set[str] = set()
        results: list[PaperRaw] = []

        for topic in topics:
            logger.info(f"Fetching arXiv papers | topic={topic!r} since={since.date()}")
            papers = self._fetch_for_topic(topic, since, seen_ids)
            results.extend(papers)
            logger.info(f"  -> {len(papers)} new papers found for {topic!r}")

        logger.info(f"Total collected: {len(results)} papers across {len(topics)} topics")
        return results

    def _fetch_for_topic(
        self,
        topic: str,
        since: datetime,
        seen_ids: set[str],
    ) -> list[PaperRaw]:
        search = arxiv.Search(
            query=topic,
            max_results=self._max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers: list[PaperRaw] = []
        for result in self._client.results(search):
            # published は timezone-aware だが念のため確認
            published = result.published
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)

            if published < since:
                # 新着順のため、これ以降は全て古い
                break

            arxiv_id = result.entry_id.split("/")[-1]
            if arxiv_id in seen_ids:
                continue

            seen_ids.add(arxiv_id)
            papers.append(
                PaperRaw(
                    arxiv_id=arxiv_id,
                    title=result.title,
                    abstract=result.summary,
                    authors=[a.name for a in result.authors],
                    published_at=published,
                    pdf_url=result.pdf_url,
                    topic=topic,
                )
            )

        return papers
