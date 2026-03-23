"""研究アイデア創出エンジン - Streamlit ホーム画面。

起動方法:
    uv run streamlit run app.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rag_paper_recommend.config.settings import settings
from rag_paper_recommend.storage.sqlite_store import SQLiteStore

st.set_page_config(
    page_title="研究アイデア創出エンジン",
    page_icon="🔬",
    layout="wide",
)


@st.cache_resource
def get_store() -> SQLiteStore:
    return SQLiteStore(settings.get_db_path())


def main() -> None:
    st.title("🔬 研究アイデア創出エンジン")
    st.caption("arXiv 論文の自動収集・分析・アイデア生成システム")

    store = get_store()

    # --- メトリクス ---
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    all_papers = store.get_papers_in_range(
        datetime(2000, 1, 1, tzinfo=timezone.utc), now
    )
    recent_papers = [p for p in all_papers if p.collected_at >= week_ago]
    extracted = [p for p in all_papers if p.extracted_at is not None]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総収集論文数", f"{len(all_papers):,} 件")
    col2.metric("抽出済み", f"{len(extracted):,} 件")
    col3.metric("直近7日", f"{len(recent_papers):,} 件")
    col4.metric("収集トピック数", f"{len(settings.get_topics())} トピック")

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("📊 トピック別収集数")
        if all_papers:
            topic_counts: dict[str, int] = {}
            for p in all_papers:
                topic_counts[p.topic] = topic_counts.get(p.topic, 0) + 1
            st.bar_chart(topic_counts)
        else:
            st.info("まだ論文が収集されていません。`uv run python main.py bootstrap` を実行してください。")

    with col_right:
        st.subheader("🕐 最新収集論文")
        latest = sorted(all_papers, key=lambda p: p.collected_at, reverse=True)[:8]
        if latest:
            for paper in latest:
                with st.container():
                    st.markdown(
                        f"**[{paper.title[:60]}{'...' if len(paper.title) > 60 else ''}]"
                        f"({paper.pdf_url})**"
                    )
                    st.caption(
                        f"`{paper.topic}` · {paper.published_at.strftime('%Y-%m-%d')}"
                    )
        else:
            st.info("論文がありません。")

    st.divider()
    st.subheader("🚀 クイックアクション")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.page_link("pages/1_papers.py", label="📄 論文を閲覧する", icon="📄")
    with c2:
        st.page_link("pages/2_search.py", label="🔍 論文を検索する", icon="🔍")
    with c3:
        st.page_link("pages/3_reports.py", label="📊 レポートを見る", icon="📊")


if __name__ == "__main__":
    main()
