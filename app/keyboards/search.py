Exit code: 0
Wall time: 0.9 seconds
Output:
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def search_results(files: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"ðŸ“ {item['name'][:52]}", callback_data=f"file:{item['_id']}")] for item in files]
    return InlineKeyboardMarkup(inline_keyboard=rows)


