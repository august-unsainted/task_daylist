from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot_config import config


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


def get_back_kb(task: dict, okay_text: bool = False) -> InlineKeyboardMarkup:
    is_completed = task['end_date'] is not None
    template_kb = 'completed' if is_completed else 'view'
    kb = config.edit_keyboard(task['id'], template_kb)
    date_info = task[f'notification_date'].split()[0]
    if is_completed:
        okay_text = True
    back_text = 'Понятно 👍' if okay_text else '◀️ Назад'
    button = btn(back_text, f'list_{date_info}')
    if len(kb.inline_keyboard) == 1:
        kb.inline_keyboard[0].append(button)
    else:
        kb.inline_keyboard.append([button])
    return kb
