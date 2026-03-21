"""論文収集レイヤーの抽象基底クラス。

新しい収集ソース（Semantic Scholar, PubMed 等）を追加する場合は
BaseCollector を継承して fetch() を実装する。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PaperRaw:
    """収集した論文の生データ。ソースに依存しない共通フォーマット。"""

    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    published_at: datetime
    pdf_url: str
    topic: str  # どのトピッククエリで収集されたか


class BaseCollector(ABC):
    """論文収集の共通インターフェース。"""

    @abstractmethod
    def fetch(self, topics: list[str], days_back: int = 1) -> list[PaperRaw]:
        """指定トピック・期間の論文を収集する。

        Args:
            topics: 検索トピックのリスト。
            days_back: 何日前までの論文を対象にするか。

        Returns:
            収集した論文リスト。arxiv_id の重複は除外済み。
        """
        ...
