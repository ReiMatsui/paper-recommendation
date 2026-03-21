"""ChromaDB を使ったベクトルストア。

論文の title + abstract を埋め込みベクトルとして保存し、
意味的に類似した論文の検索を可能にする。
埋め込みには ChromaDB 組み込みの DefaultEmbeddingFunction を使用する
（onnxruntime ベース、追加費用なし）。
"""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from loguru import logger


class VectorStore:
    """論文の類似検索用ベクトルストア。"""

    COLLECTION_NAME = "papers"

    def __init__(self, db_path: Path) -> None:
        self._client = chromadb.PersistentClient(path=str(db_path))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
        )
        logger.debug(f"VectorStore initialized | path={db_path} count={self.count()}")

    def upsert(self, arxiv_id: str, text: str, metadata: dict) -> None:
        """論文テキストをベクトル化して保存・更新する。

        Args:
            arxiv_id: 論文の一意識別子。
            text: 埋め込み対象のテキスト（title + abstract を推奨）。
            metadata: 検索結果と一緒に返すメタデータ（title, topic 等）。
        """
        self._collection.upsert(
            ids=[arxiv_id],
            documents=[text],
            metadatas=[metadata],
        )

    def search_similar(self, query: str, n_results: int = 5) -> list[dict]:
        """クエリテキストに意味的に類似した論文を検索する。

        Args:
            query: 検索クエリ文字列。
            n_results: 返す件数（上限）。

        Returns:
            類似度が高い順の論文リスト。各要素は arxiv_id, document, metadata, distance を持つ。
        """
        count = self.count()
        if count == 0:
            return []

        actual_n = min(n_results, count)
        results = self._collection.query(
            query_texts=[query],
            n_results=actual_n,
        )

        papers = []
        for i, arxiv_id in enumerate(results["ids"][0]):
            papers.append(
                {
                    "arxiv_id": arxiv_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )
        return papers

    def count(self) -> int:
        """保存済み論文数を返す。"""
        return self._collection.count()
