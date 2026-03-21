"""Markdown 形式のレポートを生成・保存する。"""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..storage.models import Paper, Synthesis


class MarkdownReporter:
    """Jinja2 テンプレートを使って Markdown レポートを生成する。

    出力先:
        日次: output_dir / YYYY-MM-DD / daily_report.md
        週次: output_dir / weekly_YYYY-MM-DD / weekly_report.md
        月次: output_dir / monthly_YYYY-MM-DD / monthly_report.md
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        template_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape([]),  # Markdown なのでエスケープ不要
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def write_daily(self, date: datetime, papers: list[Paper]) -> Path:
        """日次収集レポートを生成して保存する。"""
        template = self._env.get_template("daily_report.md.j2")
        content = template.render(date=date, papers=papers)
        return self._save(date.strftime("%Y-%m-%d"), "daily_report.md", content)

    def write_synthesis(self, synthesis: Synthesis) -> Path:
        """週次・月次合成レポートを保存する。

        synthesis_text はすでに LLM が生成した Markdown なので、
        ヘッダーとメタ情報を付加してそのまま保存する。
        """
        template = self._env.get_template("synthesis_report.md.j2")
        content = template.render(synthesis=synthesis)
        subdir = f"{synthesis.period_type}_{synthesis.period_start.strftime('%Y-%m-%d')}"
        filename = f"{synthesis.period_type}_report.md"
        return self._save(subdir, filename, content)

    def _save(self, subdir: str, filename: str, content: str) -> Path:
        report_dir = self._output_dir / subdir
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / filename
        path.write_text(content, encoding="utf-8")
        return path
