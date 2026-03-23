"""Gemini (Google) LLM クライアント。"""

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.settings import Settings
from .base import BaseLLMClient, LLMResponse


class GeminiClient(BaseLLMClient):
    """Google Gemini API クライアント。

    無料枠: gemini-1.5-flash で 1,500 リクエスト/日、100万トークン/月
    レートリミット: 15 RPM（無料枠）
    推奨モデル: gemini-1.5-flash（無料枠あり・高速）
    """

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model_name = settings.gemini_model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=15, max=120),
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2048,
        ) if system_prompt else types.GenerateContentConfig(max_output_tokens=2048)

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=config,
        )

        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

        return LLMResponse(
            content=response.text,
            provider=self.provider_name,
            model=self._model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
