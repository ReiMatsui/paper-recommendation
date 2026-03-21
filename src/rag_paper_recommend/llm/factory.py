"""LLM クライアントのファクトリ。

settings.llm_provider の値に応じて適切なクライアントを生成する。
新しいプロバイダーを追加する場合は _PROVIDER_MAP に追記するだけでよい。
"""

from ..config.settings import LLMProvider, Settings
from .base import BaseLLMClient
from .claude_client import ClaudeClient
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient

_PROVIDER_MAP: dict[LLMProvider, type[BaseLLMClient]] = {
    LLMProvider.CLAUDE: ClaudeClient,
    LLMProvider.GEMINI: GeminiClient,
    LLMProvider.OPENAI: OpenAIClient,
}


def create_llm_client(settings: Settings) -> BaseLLMClient:
    """設定に基づいて LLM クライアントを生成する。

    Args:
        settings: アプリケーション設定。

    Returns:
        設定されたプロバイダーの BaseLLMClient 実装インスタンス。

    Raises:
        ValueError: 未対応のプロバイダーが指定された場合。
    """
    client_class = _PROVIDER_MAP.get(settings.llm_provider)
    if client_class is None:
        supported = ", ".join(p.value for p in LLMProvider)
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider!r}. "
            f"Supported: {supported}"
        )
    return client_class(settings)
