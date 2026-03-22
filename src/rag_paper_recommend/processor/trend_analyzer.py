"""Stage 3: 今日の論文と過去 7 日間を比較して日次トレンドを分析する。"""

from datetime import datetime

from loguru import logger

from ..llm.base import BaseLLMClient
from ..storage.models import Paper
from .prompts import DAILY_TREND_PROMPT, TREND_ANALYSIS_SYSTEM

# 過去論文は手法フィールドのみ渡してトークンを節約
MAX_PAST_PAPERS = 50


class TrendAnalyzer:
    """今日の論文 vs 過去 7 日間の比較から日次トレンドを生成する。"""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client

    def analyze(
        self,
        today_papers: list[Paper],
        past_papers: list[Paper],
        today_date: datetime,
    ) -> str | None:
        """日次トレンド分析を生成する。

        today_papers が空でも past_papers があれば分析を実行する。
        両方空の場合のみ None を返す。
        """
        if not today_papers and not past_papers:
            logger.info("No papers available for trend analysis. Skipping.")
            return None

        # 過去論文は最新 MAX_PAST_PAPERS 件に絞る
        past_target = past_papers[:MAX_PAST_PAPERS]

        today_data = self._format_today_papers(today_papers)
        past_data = self._format_past_papers(past_target)

        prompt = DAILY_TREND_PROMPT.format(
            today_date=today_date.strftime("%Y-%m-%d"),
            today_count=len(today_papers),
            today_papers_data=today_data if today_papers else "（今日の収集論文はありませんでした）",
            past_count=len(past_target),
            past_papers_data=past_data if past_target else "（過去 7 日間の論文データがありません）",
        )

        try:
            response = self._llm.generate(prompt, system_prompt=TREND_ANALYSIS_SYSTEM)
            logger.info(
                f"Trend analysis complete | today={len(today_papers)} past={len(past_target)} "
                f"tokens_in={response.input_tokens} tokens_out={response.output_tokens}"
            )
            return response.content
        except Exception as e:
            logger.error(f"Trend analysis failed | {e}")
            return None

    @staticmethod
    def _format_today_papers(papers: list[Paper]) -> str:
        """今日の論文は全フィールドを含めてフォーマットする。"""
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

    @staticmethod
    def _format_past_papers(papers: list[Paper]) -> str:
        """過去論文はタイトルと手法のみ（トークン節約）。"""
        chunks: list[str] = []
        for i, paper in enumerate(papers, 1):
            chunk = (
                f"[過去論文 {i}] {paper.title}\n"
                f"  手法: {paper.method or '未抽出'}\n"
            )
            chunks.append(chunk)
        return "\n".join(chunks)
