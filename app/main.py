Exit code: 0
Wall time: 1.2 seconds
Output:
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.database import Database
from app.handlers import admin, common, indexing


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = Database(settings.mongo_uri, settings.mongo_db)
    await db.ensure_indexes()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(settings=settings, db=db)
    dispatcher.include_routers(admin.router, common.router, indexing.router)
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())


