"""SQLAlchemy ORM モデル定義。

papers: 論文メタデータと構造化抽出結果
syntheses: 週次・月次のトレンド合成レポート
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Paper(Base):
    """論文テーブル。

    arxiv_id をユニークキーとして重複を防ぐ。
    構造化抽出（problem / method / claims / limitations / open_questions）は
    LLM 処理後に update_extraction() で書き込む。
    """

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    pdf_url: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Stage 1: LLM による構造化抽出結果 ---
    problem: Mapped[Optional[str]] = mapped_column(Text)
    method: Mapped[Optional[str]] = mapped_column(Text)
    claims: Mapped[Optional[str]] = mapped_column(Text)
    limitations: Mapped[Optional[str]] = mapped_column(Text)
    open_questions: Mapped[Optional[str]] = mapped_column(Text)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50))
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_papers_collected_at", "collected_at"),
        Index("ix_papers_topic", "topic"),
    )

    def __repr__(self) -> str:
        return f"<Paper arxiv_id={self.arxiv_id!r} title={self.title[:40]!r}>"


class Synthesis(Base):
    """週次・月次のトレンド合成レポートテーブル。

    period_type: "weekly" または "monthly"
    synthesis_text: LLM が生成した Markdown テキスト
    """

    __tablename__ = "syntheses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    synthesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    paper_count: Mapped[int] = mapped_column(nullable=False)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_syntheses_period", "period_type", "period_start"),
    )

    def __repr__(self) -> str:
        return (
            f"<Synthesis type={self.period_type!r} "
            f"start={self.period_start.date()} topic={self.topic!r}>"
        )
