"""Entry point.

Wires configuration, sources, the pipeline, the notifier and optional Sheets
logging together, then exposes the search as Telegram commands and an optional
schedule. Secrets come from the environment; nothing sensitive is hard-coded.

Run:  python -m havenhunter.app
"""
from __future__ import annotations

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from . import config as cfg
from .dedup import InMemoryStore
from .notifier import Notifier
from .pipeline import run as run_pipeline
from .sources import available

MENU = [
    BotCommand("scan", "Search every profile now"),
    BotCommand("status", "Show configuration and pending matches"),
    BotCommand("start", "Help and command reminder"),
]


class Engine:
    """Holds shared state so command handlers stay thin."""

    def __init__(self, settings: cfg.Settings):
        self.settings = settings
        self.store = InMemoryStore()  # swap for the persistent store in production
        self.sources = available()
        self.notifier: Notifier | None = None

    async def scan_profile(self, name: str, announce_empty: bool = True) -> None:
        profile = self.settings.profiles[name]
        result = await run_pipeline(profile, self.sources, self.store)
        assert self.notifier is not None
        await self.notifier.start_review(name, result.fresh, announce_empty=announce_empty)

    async def scan_all(self, announce_empty: bool = True) -> None:
        for name in self.settings.profiles:
            await self.scan_profile(name, announce_empty=announce_empty)


async def _cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "HavenHunter is online.\n"
        "/scan to search now, /status for configuration."
    )


def build_engine_and_app() -> tuple[Engine, Application]:
    settings = cfg.load("config.yaml")
    engine = Engine(settings)
    app = (
        Application.builder()
        .token(settings.telegram_token)
        .post_init(_post_init)
        .build()
    )

    async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Searching...")
        await engine.scan_all()

    async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        lines = [f"Sources: {', '.join(engine.sources)}"]
        for profile in settings.profiles.values():
            lines.append(f"- {profile.label} (min rooms {profile.criteria.min_rooms})")
        await update.message.reply_text("\n".join(lines))

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("status", cmd_status))

    engine.notifier = Notifier(app, int(settings.telegram_chat_id), settings.profiles)
    return engine, app


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands(MENU)


def main() -> None:
    engine, app = build_engine_and_app()
    settings = engine.settings

    # Optional unattended scanning. The bot's own job queue runs the same scan
    # the /scan command triggers, on a fixed interval. Set SCAN_INTERVAL_MINUTES
    # to 0 (the default) to disable and drive it by hand instead.
    if settings.scheduled and app.job_queue is not None:
        async def _scheduled_scan(_context) -> None:
            await engine.scan_all(announce_empty=False)  # stay silent when nothing new

        app.job_queue.run_repeating(
            _scheduled_scan,
            interval=settings.scan_interval_minutes * 60,
            first=settings.scan_interval_minutes * 60,
        )
        print(f"Scheduled scan every {settings.scan_interval_minutes} min.")

    print(f"HavenHunter started. Sources: {', '.join(engine.sources)}")
    app.run_polling()


if __name__ == "__main__":
    main()
