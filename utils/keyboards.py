from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def btn(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def markup(kb: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_pagination_kb(key: str, page: int, length: int, on_page: int) -> list[InlineKeyboardButton]:
    pages_count = ceil(length / on_page)
    back_cb = f'page_{page - 1}_{key}' if page > 1 else 'null'
    next_cb = f'page_{page + 1}_{key}' if page < pages_count else 'null'
    return [btn('◀️', back_cb), btn(f'{page}/{pages_count}', 'placeholder'),
            btn('▶️', next_cb)]
