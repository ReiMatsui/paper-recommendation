"""Stage 1: 個別論文から研究構造を抽出する。"""

import json
import re
import time

from loguru import logger

from ..collector.base import PaperRaw
from ..llm.base import BaseLLMClient
from .prompts import EXTRACTION_PROMPT, EXTRACTION_SYSTEM

# Gemini 無料枠は 15 RPM のため、呼び出し間に待機する（秒）
# 4秒 = 15 req/min ちょうど。余裕を持たせて5秒に設定。
_REQUEST_INTERVAL_SEC = 5.0


class PaperExtractor:
    """LLM を使って論文から構造化データを抽出する。

    抽出する項目:
        - problem: 解決しようとしている問題
        - method: 提案手法・アプローチ
        - claims: 主な結果・主張
        - limitations: 研究の限界
        - open_questions: 今後の課題
    """

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client
        self._last_request_time: float = 0.0

    def extract(self, paper: PaperRaw) -> dict | None:
        """論文から構造化データを抽出する。

        Args:
            paper: 抽出対象の論文データ。

        Returns:
            抽出結果の辞書。LLM エラーや JSON パース失敗時は None を返す。
        """
        prompt = EXTRACTION_PROMPT.format(
            title=paper.title,
            authors=", ".join(paper.authors[:5]),  # 著者が多い場合は先頭5名
            abstract=paper.abstract,
        )
        try:
            self._wait_for_rate_limit()
            response = self._llm.generate(prompt, system_prompt=EXTRACTION_SYSTEM)
            return self._parse_json(response.content)
        except json.JSONDecodeError as e:
            logger.warning(
                f"JSON parse failed | arxiv_id={paper.arxiv_id} error={e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Extraction failed | arxiv_id={paper.arxiv_id} error={e}"
            )
            return None

    def _wait_for_rate_limit(self) -> None:
        """前回のリクエストから _REQUEST_INTERVAL_SEC 秒経過するまで待機する。"""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _REQUEST_INTERVAL_SEC:
            time.sleep(_REQUEST_INTERVAL_SEC - elapsed)
        self._last_request_time = time.monotonic()

    @staticmethod
    def _parse_json(text: str) -> dict:
        """LLM の応答から JSON を抽出してパースする。

        コードブロック（```json ... ```）で囲まれていても処理できる。
        """
        # コードブロックの除去
        cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
        cleaned = cleaned.rstrip("`").strip()
        return json.loads(cleaned)
