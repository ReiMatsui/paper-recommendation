"""Stage 4: 大量論文を2段階処理でブートストラップ分析する。

Phase 1: 論文を CHUNK_SIZE 件ずつに分割して中間サマリーを生成
Phase 2: 全中間サマリーを統合して最終レポートを生成
"""

from datetime import datetime

from loguru import logger

from ..llm.base import BaseLLMClient
from ..storage.models import Paper
from .prompts import (
    BOOTSTRAP_CHUNK_PROMPT,
    BOOTSTRAP_CHUNK_SYSTEM,
    BOOTSTRAP_FINAL_PROMPT,
    BOOTSTRAP_FINAL_SYSTEM,
)

CHUNK_SIZE = 50  # Phase 1: 1回のLLM呼び出しで処理する論文数


class BootstrapSynthesizer:
    """大量論文を2段階処理でフィールド概観レポートを生成する。"""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client

    def synthesize(
        self,
        topic: str,
        papers: list[Paper],
        start: datetime,
        end: datetime,
        days: int,
    ) -> str | None:
        """2段階処理でブートストラップ分析レポートを生成する。"""
        if not papers:
            logger.warning(f"No papers for bootstrap synthesis | topic={topic!r}")
            return None

        logger.info(
            f"Bootstrap synthesis | topic={topic!r} papers={len(papers)} "
            f"chunks={len(papers) // CHUNK_SIZE + 1}"
        )

        # Phase 1: チャンクごとの中間サマリー生成
        chunks = [papers[i:i + CHUNK_SIZE] for i in range(0, len(papers), CHUNK_SIZE)]
        summaries: list[str] = []

        for i, chunk in enumerate(chunks, 1):
            logger.info(f"  Phase 1: chunk {i}/{len(chunks)} ({len(chunk)} papers)")
            summary = self._summarize_chunk(topic, chunk, start, end, i, len(chunks))
            if summary:
                summaries.append(f"### チャンク {i}/{len(chunks)}\n{summary}")
            else:
                logger.warning(f"  Chunk {i} summary failed, skipping")

        if not summaries:
            logger.error(f"All chunks failed | topic={topic!r}")
            return None

        # Phase 2: 最終統合レポート生成
        logger.info(f"  Phase 2: final synthesis from {len(summaries)} summaries")
        return self._final_synthesis(topic, summaries, days, len(papers))

    def _summarize_chunk(
        self,
        topic: str,
        papers: list[Paper],
        start: datetime,
        end: datetime,
        chunk_idx: int,
        total_chunks: int,
    ) -> str | None:
        papers_data = self._format_papers(papers)
        prompt = BOOTSTRAP_CHUNK_PROMPT.format(
            topic=topic,
            count=len(papers),
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            papers_data=papers_data,
        )
        try:
            response = self._llm.generate(prompt, system_prompt=BOOTSTRAP_CHUNK_SYSTEM)
            return response.content
        except Exception as e:
            logger.error(f"Chunk {chunk_idx}/{total_chunks} failed | {e}")
            return None

    def _final_synthesis(
        self,
        topic: str,
        summaries: list[str],
        days: int,
        paper_count: int,
    ) -> str | None:
        prompt = BOOTSTRAP_FINAL_PROMPT.format(
            topic=topic,
            days=days,
            paper_count=paper_count,
            chunk_count=len(summaries),
            summaries="\n\n".join(summaries),
        )
        try:
            response = self._llm.generate(prompt, system_prompt=BOOTSTRAP_FINAL_SYSTEM)
            logger.info(
                f"Bootstrap final synthesis complete | topic={topic!r} "
                f"tokens_in={response.input_tokens} tokens_out={response.output_tokens}"
            )
            return response.content
        except Exception as e:
            logger.error(f"Final synthesis failed | topic={topic!r} | {e}")
            return None

    @staticmethod
    def _format_papers(papers: list[Paper]) -> str:
        chunks: list[str] = []
        for i, paper in enumerate(papers, 1):
            chunk = (
                f"[論文 {i}]\n"
                f"タイトル: {paper.title}\n"
                f"問題: {paper.problem or '未抽出'}\n"
                f"手法: {paper.method or '未抽出'}\n"
                f"主張: {paper.claims or '未抽出'}\n"
                f"今後の課題: {paper.open_questions or '未抽出'}\n"
            )
            chunks.append(chunk)
        return "\n".join(chunks)
