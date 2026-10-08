Exit code: 0
Wall time: 1.1 seconds
Output:
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import Settings
from app.database import Database

router = Router(name="admin")


def is_admin(message: Message, settings: Settings) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admins)


@router.message(Command("stats"))
async def stats(message: Message, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    values = await db.stats()
    await message.answer(f"<b>TeleVault statistics</b>\nUsers: {values['users']}\nIndexed files: {values['files']}\nOpen requests: {values['requests']}")


@router.message(Command("broadcast"))
async def broadcast(message: Message, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    if not message.reply_to_message:
        await message.answer("Reply to a message with <code>/broadcast</code>.")
        return
    sent = failed = 0
    async for user in db.db.users.find({"is_banned": {"$ne": True}}, {"user_id": 1}):
        try:
            await message.reply_to_message.copy_to(user["user_id"])
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"Broadcast complete. Sent: {sent}; failed: {failed}.")


