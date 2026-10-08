Exit code: 0
Wall time: 0.9 seconds
Output:
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
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
    await message.answer(f"<b>TeleVault statistics</b>\nUsers: {values['users']}\nPremium: {values['premium']}\nIndexed files: {values['files']}\nOpen requests: {values['requests']}")


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


@router.message(Command("ban"))
async def ban(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    try:
        user_id = int(command.args or "")
    except ValueError:
        await message.answer("Usage: <code>/ban user_id</code>")
        return
    await db.set_ban(user_id, True)
    await message.answer(f"User <code>{user_id}</code> has been banned.")


@router.message(Command("unban"))
async def unban(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    try:
        user_id = int(command.args or "")
    except ValueError:
        await message.answer("Usage: <code>/unban user_id</code>")
        return
    await db.set_ban(user_id, False)
    await message.answer(f"User <code>{user_id}</code> has been unbanned.")


@router.message(Command("maintenance"))
async def maintenance(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    option = (command.args or "").casefold()
    if option not in {"on", "off"}:
        await message.answer("Usage: <code>/maintenance on</code> or <code>/maintenance off</code>")
        return
    await db.set_maintenance(option == "on")
    await message.answer(f"Maintenance mode is now <b>{option}</b>.")


@router.message(Command("premium"))
async def premium(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    try:
        user_id, days = map(int, (command.args or "").split())
        if days < 1 or days > 3650:
            raise ValueError
    except ValueError:
        await message.answer("Usage: <code>/premium user_id days</code>")
        return
    expiry = await db.grant_premium(user_id, days)
    await message.answer(f"Premium granted to <code>{user_id}</code> until {expiry:%d %b %Y}.")


@router.message(Command("removepremium"))
async def remove_premium(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if not is_admin(message, settings):
        return
    try:
        user_id = int(command.args or "")
    except ValueError:
        await message.answer("Usage: <code>/removepremium user_id</code>")
        return
    await db.remove_premium(user_id)
    await message.answer(f"Premium removed for <code>{user_id}</code>.")

