"""論文ブラウザページ。"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_paper_recommend.config.settings import settings
from rag_paper_recommend.storage.sqlite_store import SQLiteStore

st.set_page_config(page_title="論文ブラウザ", page_icon="📄", layout="wide")


@st.cache_resource
def get_store() -> SQLiteStore:
    return SQLiteStore(settings.get_db_path())


def render_paper_card(paper) -> None:
    with st.expander(f"**{paper.title}**", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(
                f"👤 {', '.join(paper.authors[:3])}"
                f"{'他' if len(paper.authors) > 3 else ''} "
                f"· 📅 {paper.published_at.strftime('%Y-%m-%d')} "
                f"· 🏷️ `{paper.topic}`"
            )
        with col2:
            st.link_button("📄 PDF を開く", paper.pdf_url, use_container_width=True)

        if paper.problem:
            st.markdown("**🎯 解こうとしている問題**")
            st.markdown(paper.problem)
            st.markdown("**🔧 提案手法**")
            st.markdown(paper.method or "—")
            st.markdown("**✅ 主な成果・主張**")
            st.markdown(paper.claims or "—")
            if paper.limitations:
                st.markdown("**⚠️ 限界・制約**")
                st.markdown(paper.limitations)
            if paper.open_questions:
                st.markdown("**❓ 今後の課題**")
                st.markdown(paper.open_questions)
        else:
            st.info("⚠️ LLM 抽出未完了")


def main() -> None:
    st.title("📄 論文ブラウザ")

    store = get_store()
    now = datetime.now(timezone.utc)

    # --- フィルター ---
    with st.sidebar:
        st.header("フィルター")

        topics = settings.get_topics()
        selected_topics = st.multiselect(
            "トピック", options=topics, default=topics
        )

        all_papers_raw = store.get_papers_in_range(
            datetime(2000, 1, 1, tzinfo=timezone.utc), now
        )
        if all_papers_raw:
            min_date = min(p.collected_at for p in all_papers_raw).date()
            max_date = max(p.collected_at for p in all_papers_raw).date()
        else:
            from datetime import date
            min_date = max_date = date.today()

        date_range = st.date_input(
            "収集日",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        extracted_only = st.checkbox("抽出済みのみ表示", value=False)
        sort_by = st.selectbox("並び順", ["公開日（新しい順）", "公開日（古い順）", "収集日（新しい順）"])

    # --- フィルタリング ---
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_dt = datetime.combine(date_range[0], datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(date_range[1], datetime.max.time()).replace(tzinfo=timezone.utc)
    else:
        start_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
        end_dt = now

    papers = store.get_papers_in_range(start_dt, end_dt) if extracted_only else [
        p for p in all_papers_raw
        if p.collected_at >= start_dt and p.collected_at <= end_dt
    ]

    if selected_topics:
        papers = [p for p in papers if p.topic in selected_topics]

    # ソート
    if sort_by == "公開日（新しい順）":
        papers.sort(key=lambda p: p.published_at, reverse=True)
    elif sort_by == "公開日（古い順）":
        papers.sort(key=lambda p: p.published_at)
    else:
        papers.sort(key=lambda p: p.collected_at, reverse=True)

    st.caption(f"表示中: **{len(papers)}** 件")

    if not papers:
        st.info("条件に一致する論文がありません。")
        return

    for paper in papers:
        render_paper_card(paper)


if __name__ == "__main__":
    main()
