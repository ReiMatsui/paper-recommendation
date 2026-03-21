"""APScheduler を使ったジョブスケジューラ。

毎日定時に DailyPipeline を実行し、
毎週月曜・毎月 1 日に SynthesisPipeline を実行する。
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from ..config.settings import Settings
from ..pipeline.daily_pipeline import DailyPipeline
from ..pipeline.synthesis_pipeline import SynthesisPipeline


class JobScheduler:
    """ジョブのスケジューリングと管理を担当する。"""

    def __init__(
        self,
        settings: Settings,
        daily_pipeline: DailyPipeline,
        synthesis_pipeline: SynthesisPipeline,
    ) -> None:
        self._scheduler = BlockingScheduler(timezone="Asia/Tokyo")
        self._daily = daily_pipeline
        self._synthesis = synthesis_pipeline
        self._register_jobs(settings)

    def _register_jobs(self, settings: Settings) -> None:
        hour, minute = map(int, settings.daily_schedule_time.split(":"))
        # 合成ジョブは日次の 1 時間後に設定（日次完了を待つ簡易的な方法）
        synthesis_hour = (hour + 1) % 24

        # --- 日次: 毎日 daily_schedule_time に実行 ---
        self._scheduler.add_job(
            self._daily.run,
            CronTrigger(hour=hour, minute=minute),
            id="daily_pipeline",
            name="Daily paper collection & extraction",
            misfire_grace_time=3600,
            coalesce=True,
        )

        # --- 週次: 毎週 weekly_schedule_day の synthesis_hour に実行 ---
        self._scheduler.add_job(
            self._synthesis.run_weekly,
            CronTrigger(
                day_of_week=settings.weekly_schedule_day,
                hour=synthesis_hour,
                minute=minute,
            ),
            id="weekly_synthesis",
            name="Weekly trend synthesis",
            misfire_grace_time=3600,
            coalesce=True,
        )

        # --- 月次: 毎月 1 日の synthesis_hour に実行 ---
        self._scheduler.add_job(
            self._synthesis.run_monthly,
            CronTrigger(day=1, hour=synthesis_hour, minute=minute),
            id="monthly_synthesis",
            name="Monthly trend synthesis",
            misfire_grace_time=3600,
            coalesce=True,
        )

        logger.info("Registered jobs:")
        for job in self._scheduler.get_jobs():
            logger.info(f"  [{job.id}] {job.name} | trigger={job.trigger}")

    def start(self) -> None:
        """スケジューラを起動してブロッキング待機する（Ctrl+C で終了）。"""
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped.")
