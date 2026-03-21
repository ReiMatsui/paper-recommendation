"""アプリケーション設定。

pydantic-settings で .env を読み込み、型安全な設定オブジェクトを提供する。
LLM_PROVIDER を切り替えるだけで使用するプロバイダーを変更できる。
"""

from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # .env に未定義フィールドがあっても無視する
    )

    # --- LLM プロバイダー選択 ---
    llm_provider: LLMProvider = LLMProvider.GEMINI

    # --- Claude (Anthropic) ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"

    # --- Gemini (Google) ---
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- arXiv 収集設定 ---
    # pydantic-settings v2 は list[str] を JSON として解釈するため str で受け取り、
    # get_topics() でカンマ区切りパースする
    arxiv_topics: str = "RAG,retrieval augmented generation"
    arxiv_max_results_per_topic: int = 20
    arxiv_days_back: int = 1

    # --- スケジュール ---
    daily_schedule_time: str = "09:00"   # HH:MM (JST)
    weekly_schedule_day: str = "mon"     # mon / tue / wed / thu / fri / sat / sun

    # --- パス ---
    db_path: str = "data/db/papers.db"
    vector_db_path: str = "data/vector/chroma"
    output_dir: str = "output/reports"

    def get_topics(self) -> list[str]:
        """ARXIV_TOPICS をカンマ区切りでパースして返す。"""
        return [t.strip() for t in self.arxiv_topics.split(",") if t.strip()]

    def get_db_path(self) -> Path:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_vector_db_path(self) -> Path:
        path = Path(self.vector_db_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_output_dir(self) -> Path:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


# アプリケーション全体で共有するシングルトン設定インスタンス
settings = Settings()
