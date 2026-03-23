"""SQLite を使ったメタデータ・抽出結果の永続化。"""

from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Paper, Synthesis


class SQLiteStore:
    """論文メタデータと合成レポートを SQLite に保存・取得する。"""

    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        # expire_on_commit=False: コミット後もオブジェクトの属性をメモリに保持し、
        # セッション外でも DetachedInstanceError を起こさないようにする
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)
        logger.debug(f"SQLiteStore initialized | db={db_path}")

    # ------------------------------------------------------------------ #
    # Paper                                                                #
    # ------------------------------------------------------------------ #

    def exists(self, arxiv_id: str) -> bool:
        """指定 arxiv_id の論文が既に保存されているか確認する。"""
        with self._Session() as session:
            return (
                session.scalar(select(Paper.id).where(Paper.arxiv_id == arxiv_id))
                is not None
            )

    def save_paper(self, paper: Paper) -> None:
        """論文を保存する。重複する arxiv_id の場合はスキップする。"""
        with self._Session() as session:
            session.add(paper)
            session.commit()

    def update_extraction(
        self, arxiv_id: str, extraction: dict, llm_provider: str
    ) -> None:
        """LLM による構造化抽出結果を既存レコードに書き込む。"""
        with self._Session() as session:
            paper = session.scalar(select(Paper).where(Paper.arxiv_id == arxiv_id))
            if paper is None:
                logger.warning(f"Paper not found for extraction update | arxiv_id={arxiv_id}")
                return

            paper.problem = extraction.get("problem")
            paper.method = extraction.get("method")
            paper.claims = extraction.get("claims")
            paper.limitations = extraction.get("limitations")
            paper.open_questions = extraction.get("open_questions")
            paper.llm_provider = llm_provider
            paper.extracted_at = datetime.now(timezone.utc)
            session.commit()

    def get_papers_by_date(self, date: datetime) -> list[Paper]:
        """指定した日に収集された論文を返す。"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        with self._Session() as session:
            papers = list(
                session.scalars(
                    select(Paper)
                    .where(Paper.collected_at.between(start, end))
                    .order_by(Paper.published_at.desc())
                ).all()
            )
            # セッション外で使えるよう属性をロードしておく
            for p in papers:
                _ = p.authors
            return papers

    def get_papers_in_range(self, start: datetime, end: datetime) -> list[Paper]:
        """指定期間に収集され、かつ構造化抽出済みの論文を返す。"""
        with self._Session() as session:
            papers = list(
                session.scalars(
                    select(Paper)
                    .where(Paper.collected_at.between(start, end))
                    .where(Paper.extracted_at.is_not(None))
                    .order_by(Paper.published_at.desc())
                ).all()
            )
            for p in papers:
                _ = p.authors
            return papers

    def get_unextracted_papers(self, limit: int = 100) -> list[Paper]:
        """未抽出の論文を公開日の新しい順に最大 limit 件返す。"""
        with self._Session() as session:
            papers = list(
                session.scalars(
                    select(Paper)
                    .where(Paper.extracted_at.is_(None))
                    .order_by(Paper.published_at.desc())
                    .limit(limit)
                ).all()
            )
            for p in papers:
                _ = p.authors
            return papers

    def get_past_extracted_papers(self, before: datetime, days: int) -> list[Paper]:
        """指定日より前の N 日間に収集された抽出済み論文を返す（トレンド比較用）。"""
        from datetime import timedelta
        end = before.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=days)
        with self._Session() as session:
            papers = list(
                session.scalars(
                    select(Paper)
                    .where(Paper.collected_at.between(start, end))
                    .where(Paper.extracted_at.is_not(None))
                    .order_by(Paper.published_at.desc())
                ).all()
            )
            for p in papers:
                _ = p.authors
            return papers

    # ------------------------------------------------------------------ #
    # Synthesis                                                            #
    # ------------------------------------------------------------------ #

    def save_synthesis(self, synthesis: Synthesis) -> None:
        """合成レポートを保存する。"""
        with self._Session() as session:
            session.add(synthesis)
            session.commit()
