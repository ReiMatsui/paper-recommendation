"""Gmail SMTP を使ったメール通知モジュール。

EMAIL_ENABLED=true のときのみ送信する。
標準ライブラリのみで動作し、追加依存なし。
"""

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from loguru import logger


class EmailNotifier:
    """Gmail SMTP でレポートをメール送信する。"""

    def __init__(
        self,
        enabled: bool,
        smtp_host: str,
        smtp_port: int,
        email_from: str,
        email_password: str,
        email_to: str,
    ) -> None:
        self._enabled = enabled
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._email_from = email_from
        self._email_password = email_password
        self._email_to = email_to

    def send_daily_report(self, date: datetime, report_path: Path, paper_count: int) -> None:
        """日次レポートをメールで送信する。"""
        if not self._enabled:
            logger.debug("Email notification is disabled. Skipping.")
            return

        subject = f"[論文レポート] {date.strftime('%Y年%m月%d日')} — {paper_count}件"
        body = report_path.read_text(encoding="utf-8") if report_path.exists() else "レポートの生成に失敗しました。"
        self._send(subject, body)

    def send_synthesis_report(self, period_type: str, date: datetime, report_path: Path, paper_count: int) -> None:
        """週次・月次合成レポートをメールで送信する。"""
        if not self._enabled:
            logger.debug("Email notification is disabled. Skipping.")
            return

        label = "週次" if period_type == "weekly" else "月次"
        subject = f"[論文レポート] {label}トレンド {date.strftime('%Y年%m月%d日')} — {paper_count}件"
        body = report_path.read_text(encoding="utf-8") if report_path.exists() else "レポートの生成に失敗しました。"
        self._send(subject, body)

    def _send(self, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._email_from
        msg["To"] = self._email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self._email_from, self._email_password)
                server.send_message(msg)
            logger.info(f"Email sent | to={self._email_to} | subject={subject}")
        except Exception as e:
            logger.error(f"Failed to send email | {e}")
