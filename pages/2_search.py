"""セマンティック検索ページ。"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_paper_recommend.config.settings import settings
from rag_paper_recommend.storage.vector_store import VectorStore

st.set_page_config(page_title="論文検索", page_icon="🔍", layout="wide")


@st.cache_resource
def get_vector_store() -> VectorStore:
    return VectorStore(settings.get_vector_db_path())


def main() -> None:
    st.title("🔍 論文検索")
    st.caption("蓄積した論文からセマンティック検索（意味的な類似度で検索）")

    query = st.text_input(
        "検索クエリ",
        placeholder="例: RAG with graph neural networks / 知識グラフを使った質問応答",
    )
    n_results = st.slider("表示件数", min_value=1, max_value=20, value=5)

    if not query:
        st.info("検索ワードを入力してください。日本語・英語どちらでも検索できます。")
        return

    store = get_vector_store()

    with st.spinner("検索中..."):
        results = store.search_similar(query, n_results=n_results)

    if not results:
        st.warning("結果が見つかりませんでした。論文を収集してから検索してください。")
        return

    st.success(f"{len(results)} 件見つかりました")

    for i, result in enumerate(results, 1):
        meta = result.get("metadata", {})
        title = meta.get("title", "Unknown")
        topic = meta.get("topic", "")
        arxiv_id = result.get("arxiv_id", "")
        distance = result.get("distance", 1.0)
        similarity = max(0.0, 1.0 - distance)

        with st.expander(f"**{i}. {title}**", expanded=(i == 1)):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.caption(f"🏷️ `{topic}` · 📄 `{arxiv_id}`")
                st.progress(similarity, text=f"類似度: {similarity:.0%}")
            with col2:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
                st.link_button("PDF を開く", pdf_url, use_container_width=True)


if __name__ == "__main__":
    main()
