import re
from typing import Callable

import humanize
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

from bot_config import *
from utils.keyboards import get_pagination_kb, btn, markup, get_back_kb
from utils.time import get_weekday, to_db_str, reformat_db_str, get_tomorrow, format_date, delta, fmt, today

_t = humanize.i18n.activate("ru_RU")

router = Router()


def get_id(callback: CallbackQuery) -> str:
    return callback.data.split('_')[-1]


def get_func(is_list: bool):
    return get_list if is_list else get_completed


def generate_tasks_kb(callback: str, tasks: list[dict[str, str]], page: int | str, format_func: Callable) -> tuple[list[list[InlineKeyboardButton]], bool]:
    kb = []
    page = int(page)
    i = page - 1
    start = i * config.entries_on_page
    end = start + config.entries_on_page
    page_tasks = tasks[start:end]
    for task in page_tasks:
        text, date = task['text'], task['end_date'] or task['notification_date']
        if ':' in date:
            text = format_func(date) + ' ' + text
        if len(text) > config.btn_length:
            text = text[:config.btn_length + 1].strip() + '…'
        kb.append([btn(text, f"view_{task['id']}")])

    additional = False
    if not page_tasks:
        additional = True
    elif len(tasks) > config.entries_on_page:
        kb.append(get_pagination_kb(callback, page, len(tasks), config.entries_on_page))
    return kb, additional


def get_navigation(date: datetime, days: int, callback: str) -> list[InlineKeyboardButton]:
    row = []
    for btn_text in ['◀️ Назад', '▶️ Далее']:
        date_result = delta(date, days, '◀️' in btn_text)
        row.append(btn(btn_text, f'{callback}_{fmt(date_result)}'))
    return row


def get_completed(date_str: str, user_id: int, page: int | str) -> tuple[str, InlineKeyboardMarkup]:
    date = datetime.strptime(date_str, '%Y-%m-%d')
    mon = delta(date, date.weekday(), True)
    sun = delta(date, 6 - date.weekday())
    next_mon = delta(sun, 1)
    query = '''
        select * from tasks
        where end_date is not NULL and end_date between ? and ? and user_id = ?
        order by end_date
    '''
    tasks = db.execute_query(query, fmt(mon), fmt(next_mon), user_id)
    reg = r'\d{4}-(\d{2})-(\d{2}) \d{2}:\d{2}'
    kb, additional = generate_tasks_kb(fmt(mon) + '_week', tasks, page,
                                       lambda input_date: re.sub(reg, r'\2.\1', input_date))
    kb.append(get_navigation(date, 7, 'completed'))
    kb.append(config.keyboards.get('switch_tasks').inline_keyboard[0])
    text = texts.get('completed_tasks').format(get_weekday(mon).split(',')[0], get_weekday(sun).split(',')[0])
    if additional:
        text += '\n\n' + texts.get(f'no_completed_tasks')
    return text, markup(kb)


def get_list(date_str: str, user_id: int, page: int | str) -> tuple[str, InlineKeyboardMarkup]:
    date = datetime.strptime(date_str, '%Y-%m-%d')
    natural_day = format_date(date)
    query = '''
        select * from tasks
        where notification_date like ? and end_date is NULL and user_id = ?
        order by
            case when notification_date not like '%:%' THEN 1 ELSE 0 END,
            notification_date,
            creation_date desc
    '''
    tasks = db.execute_query(query, date_str + '%', user_id)
    kb, additional = generate_tasks_kb(fmt(date), tasks, page, lambda input_date: input_date.split()[-1][:-3])
    text = texts.get('tasks').format(natural_day)
    if 'сегодня' in natural_day:
        text = texts.get('today_emoji') + text[1:]
        tomorrow = to_db_str(get_tomorrow()).split()[0]
        kb.append([btn('Задачи на завтра ▶\uFE0F', f'list_{tomorrow}')])
    else:
        kb.append(get_navigation(date, 1, 'list'))
    kb.append(config.keyboards.get('switch_tasks').inline_keyboard[1])
    if additional:
        text += '\n\n' + texts.get(f'no_tasks')
    return text, markup(kb)


@router.message(Command('list', 'completed'))
async def view_tasks(message: Message):
    func = get_func(message.text.startswith('/list'))
    text, kb = func(today(), message.from_user.id, 1)
    await message.answer(text=text, reply_markup=kb, parse_mode='HTML')
    await message.delete()


@router.callback_query(F.data.startswith(('list', 'completed')))
async def view_tasks(callback: CallbackQuery):
    date_str = get_id(callback) if '_' in callback.data else today()
    func = get_func(callback.data.startswith('list'))
    text, kb = func(date_str, callback.from_user.id, 1)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data.startswith('view'))
async def view_task(callback: CallbackQuery):
    task_id = get_id(callback)
    task = db.execute_query('select * from tasks where id = ? order by notification_date', task_id)[0]
    text = f'{task['text']}\n\n🕓 Создано: {reformat_db_str(task['creation_date'])}'
    if task['end_date']:
        text += f'\n✅ Выполнено: {reformat_db_str(task['end_date'])}'
    await callback.message.edit_text(text=text, reply_markup=get_back_kb(task))


@router.callback_query(F.data.startswith('page'))
async def view_page(callback: CallbackQuery):
    page, date_str = callback.data.split('_')[1:3]
    func = get_func(not callback.data.endswith('week'))
    text, kb = func(date_str, callback.from_user.id, page)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data == 'null')
async def null_cb(callback: CallbackQuery):
    await callback.answer('😢 Нет значений!')
