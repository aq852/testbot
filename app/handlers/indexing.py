Exit code: 0
Wall time: 0.9 seconds
Output:
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.database import Database

router = Router(name="indexing")


@router.channel_post(F.document | F.video | F.audio)
async def index_media(message: Message, db: Database) -> None:
    media = message.document or message.video or message.audio
    if not media:
        return
    name = getattr(media, "file_name", None) or getattr(media, "title", None) or f"file-{message.message_id}"
    await db.save_file(chat_id=message.chat.id, message_id=message.message_id, file_id=media.file_id,
                       name=name, size=media.file_size or 0, kind=media.__class__.__name__.lower())


