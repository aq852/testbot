Exit code: 0
Wall time: 1.2 seconds
Output:
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from bson import ObjectId

from app.config import Settings
from app.database import Database
from app.keyboards.search import search_results

router = Router(name="common")


def human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return "0 B"


@router.message(Command("start"))
async def start(message: Message, command: CommandObject, db: Database, settings: Settings) -> None:
    if message.from_user:
        await db.upsert_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    payload = command.args or ""
    if payload.startswith("ref_"):
        try:
            referrer_id = int(payload.removeprefix("ref_"))
        except ValueError:
            referrer_id = 0
        if referrer_id and await db.claim_referral(referrer_id, message.from_user.id, settings.referral_reward_days):
            await message.answer("Referral accepted. Your friend received their premium reward.")
            return
    if payload.startswith("batch_"):
        batch = await db.get_batch(payload.removeprefix("batch_"))
        if not batch:
            await message.answer("This batch link is expired or invalid.")
            return
        delivered = 0
        for raw_id in batch["file_ids"]:
            if ObjectId.is_valid(raw_id):
                item = await db.db.files.find_one({"_id": ObjectId(raw_id)})
                if item:
                    allowed, _ = await db.consume_delivery(message.from_user.id, settings.free_daily_file_limit)
                    if not allowed:
                        break
                    await message.bot.copy_message(message.from_user.id, item["chat_id"], item["message_id"])
                    delivered += 1
        await message.answer(f"Delivered {delivered} file(s) from your batch.")
        return
    await message.answer("<b>Welcome to TeleVault</b>\n\nSearch your library with <code>/search title</code>.\nUse <code>/request title</code> when a file is missing.\n\nUse <code>/batch_done</code> after adding files to create a batch link.")


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer("<b>TeleVault commands</b>\n/search &lt;title&gt; â€” find a file\n/request &lt;title&gt; â€” request a title\n/profile â€” view your access\n\nAdmins: /stats, /broadcast (reply to a message)")


@router.message(Command("search"))
async def search(message: Message, command: CommandObject, db: Database) -> None:
    query = (command.args or "").strip()
    if len(query) < 2:
        await message.answer("Usage: <code>/search movie or series name</code>")
        return
    files = await db.search_files(query)
    if not files:
        await message.answer("No matching files found. Use <code>/request title</code> to request it.")
        return
    await message.answer(f"<b>Results for:</b> {query}", reply_markup=search_results(files))


@router.callback_query(F.data.startswith("file:"))
async def deliver_file(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    raw_id = callback.data.removeprefix("file:") if callback.data else ""
    if not ObjectId.is_valid(raw_id):
        await callback.answer("This file link has expired.", show_alert=True)
        return
    item = await db.db.files.find_one({"_id": ObjectId(raw_id)})
    if not item or not callback.message:
        await callback.answer("File not found.", show_alert=True)
        return
    allowed, remaining = await db.consume_delivery(callback.from_user.id, settings.free_daily_file_limit)
    if not allowed:
        await callback.answer("Your daily free download limit is reached. Use /plan for premium access.", show_alert=True)
        return
    try:
        await callback.message.bot.copy_message(callback.from_user.id, item["chat_id"], item["message_id"])
    except Exception:
        await callback.answer("Start the bot in private chat first, then try again.", show_alert=True)
        return
    suffix = "" if remaining < 0 else f" {remaining} free delivery(ies) left today."
    await callback.answer(f"Sent in private chat.{suffix}")


@router.callback_query(F.data.startswith("batch:add:"))
async def add_to_batch(callback: CallbackQuery, db: Database) -> None:
    raw_id = callback.data.removeprefix("batch:add:") if callback.data else ""
    if not ObjectId.is_valid(raw_id):
        await callback.answer("This file link has expired.", show_alert=True)
        return
    count = await db.add_to_batch(callback.from_user.id, raw_id)
    await callback.answer(f"Added to your batch ({count} file(s)).")


@router.message(Command("batch_done"))
async def batch_done(message: Message, db: Database) -> None:
    batch = await db.finish_batch(message.from_user.id)
    if not batch:
        await message.answer("Your batch is empty. Search for files and use Add to batch first.")
        return
    me = await message.bot.get_me()
    await message.answer(f"Your batch link (valid for 24 hours):\nhttps://t.me/{me.username}?start=batch_{batch['batch_id']}")


@router.message(Command("request"))
async def request_file(message: Message, command: CommandObject, db: Database) -> None:
    query = (command.args or "").strip()
    if len(query) < 2:
        await message.answer("Usage: <code>/request title</code>")
        return
    await db.create_request(message.from_user.id, query)
    await message.answer("Your request has been saved. Weâ€™ll notify you when it is added.")


@router.message(Command("profile"))
async def profile(message: Message, db: Database, settings: Settings) -> None:
    premium, remaining, expiry = await db.get_access(message.from_user.id, settings.free_daily_file_limit)
    tier = "Premium" if premium else "Free"
    detail = "Unlimited deliveries" if premium else f"{remaining}/{settings.free_daily_file_limit} free deliveries remaining today"
    if premium and expiry:
        detail += f"\nPremium until: {expiry:%d %b %Y}"
    await message.answer(f"<b>TeleVault profile</b>\nAccess: <b>{tier}</b>\n{detail}")


@router.message(Command("plan"))
async def plan(message: Message, settings: Settings) -> None:
    await message.answer(f"<b>TeleVault Premium</b>\nPremium members have unlimited deliveries. Free members receive {settings.free_daily_file_limit} per day. Contact an admin to purchase or use <code>/refer</code> to earn {settings.referral_reward_days} premium days per referral.")


@router.message(Command("refer"))
async def refer(message: Message, settings: Settings) -> None:
    me = await message.bot.get_me()
    await message.answer(f"Invite link:\nhttps://t.me/{me.username}?start=ref_{message.from_user.id}\n\nYou receive {settings.referral_reward_days} premium days when a new user starts the bot with this link.")

