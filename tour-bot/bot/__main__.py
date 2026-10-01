import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.ai import AIService, ClaudeAI
from bot.config import Settings
from bot.db.session import create_tables, make_engine, make_sessionmaker
from bot.handlers import admin, ai_chat, booking, start, tours
from bot.middlewares import DbSessionMiddleware


def build_dispatcher(settings: Settings, sessionmaker, ai: AIService | None = None) -> Dispatcher:
    dp = Dispatcher(settings=settings, ai=ai)
    dp.update.outer_middleware(DbSessionMiddleware(sessionmaker))
    # admin first so /addtour steps win over user handlers for admins; AI chat last as the catch-all
    dp.include_routers(admin.router, booking.router, start.router, tours.router, ai_chat.router)
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    engine = make_engine(settings.database_url)
    await create_tables(engine)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    ai = ClaudeAI(settings.anthropic_api_key, settings.anthropic_model) if settings.anthropic_api_key else None
    if ai is None:
        logging.warning("ANTHROPIC_API_KEY is not set: AI assistant is off, questions go straight to the admin")
    dp = build_dispatcher(settings, make_sessionmaker(engine), ai)
    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
