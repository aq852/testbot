Exit code: 0
Wall time: 0.9 seconds
Output:
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings
from app.database import Database


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)
        db: Database = data["db"]
        settings: Settings = data["settings"]
        is_admin = user.id in settings.admins
        await db.upsert_user(user.id, user.full_name, user.username)
        if not is_admin and await db.is_banned(user.id):
            await self._deny(event, "Your access to TeleVault is disabled.")
            return None
        if not is_admin and await db.maintenance_enabled():
            await self._deny(event, "TeleVault is under maintenance. Please try again shortly.")
            return None
        if not is_admin and settings.force_sub_channels:
            bot: Bot = data["bot"]
            for channel_id in settings.force_sub_channels:
                try:
                    member = await bot.get_chat_member(channel_id, user.id)
                    if member.status not in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
                        continue
                except Exception:
                    pass
                await self._deny(event, "Please join the required channel(s), then try again.")
                return None
        return await handler(event, data)

    @staticmethod
    async def _deny(event: TelegramObject, text: str) -> None:
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)

