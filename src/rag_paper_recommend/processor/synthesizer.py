"""Stage 2: 複数論文を横断してトレンドを合成する。"""

from datetime import datetime

from loguru import logger

from ..llm.base import BaseLLMClient
from ..storage.models import Paper
from .prompts import (
    MONTHLY_SYNTHESIS_PROMPT,
    SYNTHESIS_SYSTEM,
    WEEKLY_SYNTHESIS_PROMPT,
)

# 1 回の LLM 呼び出しに含める論文数の上限
# トークン数の膨張を防ぐ（多すぎると重要情報が薄まる問題もある）
MAX_PAPERS_PER_SYNTHESIS = 30


class ResearchSynthesizer:
    """複数論文のデータを横断分析し、トレンドレポートを生成する。"""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client

    def synthesize_weekly(
        self,
        topic: str,
        papers: list[Paper],
        start: datetime,
        end: datetime,
    ) -> str | None:
        """週次トレンドレポートを生成する。"""
        return self._synthesize(topic, papers, start, end, WEEKLY_SYNTHESIS_PROMPT)

    def synthesize_monthly(
        self,
        topic: str,
        papers: list[Paper],
        start: datetime,
        end: datetime,
    ) -> str | None:
        """月次トレンドレポートを生成する。"""
        return self._synthesize(topic, papers, start, end, MONTHLY_SYNTHESIS_PROMPT)

    def _synthesize(
        self,
        topic: str,
        papers: list[Paper],
        start: datetime,
        end: datetime,
        template: str,
    ) -> str | None:
        if not papers:
            logger.warning(f"No papers to synthesize | topic={topic!r}")
            return None

        # 論文数が多い場合は最新 N 件に絞る
        target_papers = papers[:MAX_PAPERS_PER_SYNTHESIS]
        if len(papers) > MAX_PAPERS_PER_SYNTHESIS:
            logger.info(
                f"Truncating papers for synthesis | "
                f"total={len(papers)} using={MAX_PAPERS_PER_SYNTHESIS}"
            )

        papers_data = self._format_papers(target_papers)
        prompt = template.format(
            topic=topic,
            count=len(target_papers),
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            papers_data=papers_data,
        )

        try:
            response = self._llm.generate(prompt, system_prompt=SYNTHESIS_SYSTEM)
            logger.info(
                f"Synthesis complete | topic={topic!r} "
                f"papers={len(target_papers)} "
                f"tokens_in={response.input_tokens} tokens_out={response.output_tokens}"
            )
            return response.content
        except Exception as e:
            logger.error(f"Synthesis failed | topic={topic!r} error={e}")
            return None

    @staticmethod
    def _format_papers(papers: list[Paper]) -> str:
        """論文リストを LLM に渡すテキスト形式にフォーマットする。"""
        chunks: list[str] = []
        for i, paper in enumerate(papers, 1):
            chunk = (
                f"[論文 {i}]\n"
                f"タイトル: {paper.title}\n"
                f"問題: {paper.problem or '未抽出'}\n"
                f"手法: {paper.method or '未抽出'}\n"
                f"主張: {paper.claims or '未抽出'}\n"
                f"限界: {paper.limitations or '未抽出'}\n"
                f"今後の課題: {paper.open_questions or '未抽出'}\n"
            )
            chunks.append(chunk)
        return "\n".join(chunks)
