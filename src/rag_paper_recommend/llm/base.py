"""LLM クライアントの抽象基底クラス。

新しいプロバイダーを追加する場合は BaseLLMClient を継承し、
generate() と provider_name, model_name プロパティを実装する。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """LLM からの応答を統一フォーマットで保持する。"""

    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMClient(ABC):
    """LLM プロバイダーの共通インターフェース。"""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        """プロンプトを送信してテキストを生成する。

        Args:
            prompt: ユーザーへのプロンプト文字列。
            system_prompt: システムプロンプト（省略可）。

        Returns:
            生成結果を含む LLMResponse。
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー識別名（例: "gemini", "claude", "openai"）。"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """使用するモデル名。"""
        ...
