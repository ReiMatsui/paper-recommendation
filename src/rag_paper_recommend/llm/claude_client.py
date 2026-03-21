"""Claude (Anthropic) LLM クライアント。"""

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.settings import Settings
from .base import BaseLLMClient, LLMResponse


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API クライアント。

    無料枠: なし（従量課金）
    推奨モデル: claude-haiku-4-5-20251001（低コスト・高速）
    """

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)
        content = response.content[0].text

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
