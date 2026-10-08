Exit code: 0
Wall time: 0.7 seconds
Output:
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def search_results(files: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in files:
        rows.append([InlineKeyboardButton(text=f"ðŸ“ {item['name'][:52]}", callback_data=f"file:{item['_id']}")])
        rows.append([InlineKeyboardButton(text="âž• Add to batch", callback_data=f"batch:add:{item['_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

