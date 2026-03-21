"""OpenAI LLM クライアント。"""

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.settings import Settings
from .base import BaseLLMClient, LLMResponse


class OpenAIClient(BaseLLMClient):
    """OpenAI API クライアント。

    無料枠: 新規アカウントに限り試用クレジットあり
    推奨モデル: gpt-4o-mini（低コスト・高速）
    """

    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=2048,
        )
        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
