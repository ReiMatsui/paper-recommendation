"""レポート閲覧ページ。"""

import sys
import threading
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_paper_recommend.config.settings import settings

st.set_page_config(page_title="レポート", page_icon="📊", layout="wide")

OUTPUT_DIR = settings.get_output_dir()


def get_report_dirs(prefix: str) -> list[Path]:
    """指定プレフィックスのレポートディレクトリを日付降順で返す。"""
    dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and d.name.startswith(prefix)],
        reverse=True,
    )
    return dirs


def run_pipeline_async() -> None:
    """バックグラウンドで日次パイプラインを実行する。"""
    from rag_paper_recommend.container import build_daily_pipeline
    build_daily_pipeline(settings).run()


def main() -> None:
    st.title("📊 レポート")

    tab_daily, tab_weekly, tab_monthly, tab_bootstrap = st.tabs(
        ["📅 日次", "📆 週次", "🗓️ 月次", "🚀 Bootstrap"]
    )

    with tab_daily:
        st.subheader("日次レポート")

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 今すぐ生成", use_container_width=True):
                with st.spinner("パイプライン実行中..."):
                    t = threading.Thread(target=run_pipeline_async)
                    t.start()
                    t.join(timeout=300)
                st.success("完了しました。ページをリロードしてください。")

        dirs = get_report_dirs("20")  # YYYY-MM-DD 形式
        if not dirs:
            st.info("日次レポートがまだありません。")
        else:
            selected = col1.selectbox(
                "日付を選択",
                options=[d.name for d in dirs],
                key="daily_date",
            )
            report_path = OUTPUT_DIR / selected / "daily_report.md"
            if report_path.exists():
                content = report_path.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button(
                    "⬇️ ダウンロード",
                    data=content,
                    file_name=f"daily_report_{selected}.md",
                    mime="text/markdown",
                )
            else:
                st.warning("レポートファイルが見つかりません。")

    with tab_weekly:
        st.subheader("週次レポート")
        dirs = get_report_dirs("weekly_")
        if not dirs:
            st.info("週次レポートがまだありません。`uv run python main.py run --weekly` で生成できます。")
        else:
            selected = st.selectbox("週を選択", options=[d.name for d in dirs], key="weekly_date")
            report_path = OUTPUT_DIR / selected / "weekly_report.md"
            if report_path.exists():
                content = report_path.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button("⬇️ ダウンロード", data=content, file_name=f"{selected}.md", mime="text/markdown")

    with tab_monthly:
        st.subheader("月次レポート")
        dirs = get_report_dirs("monthly_")
        if not dirs:
            st.info("月次レポートがまだありません。`uv run python main.py run --monthly` で生成できます。")
        else:
            selected = st.selectbox("月を選択", options=[d.name for d in dirs], key="monthly_date")
            report_path = OUTPUT_DIR / selected / "monthly_report.md"
            if report_path.exists():
                content = report_path.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button("⬇️ ダウンロード", data=content, file_name=f"{selected}.md", mime="text/markdown")

    with tab_bootstrap:
        st.subheader("Bootstrap フィールド概観レポート")
        dirs = get_report_dirs("bootstrap_")
        if not dirs:
            st.info("Bootstrap レポートがまだありません。`uv run python main.py bootstrap` で生成できます。")
        else:
            selected = st.selectbox("日付を選択", options=[d.name for d in dirs], key="bootstrap_date")
            bootstrap_dir = OUTPUT_DIR / selected
            md_files = list(bootstrap_dir.glob("*.md"))
            if not md_files:
                st.warning("レポートファイルが見つかりません。")
            else:
                for md_file in md_files:
                    st.markdown(f"### {md_file.stem}")
                    content = md_file.read_text(encoding="utf-8")
                    st.markdown(content)
                    st.download_button(
                        f"⬇️ {md_file.name} をダウンロード",
                        data=content,
                        file_name=md_file.name,
                        mime="text/markdown",
                        key=str(md_file),
                    )


if __name__ == "__main__":
    main()
