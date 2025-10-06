import re
from datetime import datetime, timedelta

import humanize
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

from bot_config import *
from utils.keyboards import get_pagination_kb, btn, markup, get_back_kb
from utils.time import now_date, get_weekday, to_db_str, reformat_db_str, get_tomorrow, get_week, format_date

_t = humanize.i18n.activate("ru_RU")

router = Router()


def get_id(callback: CallbackQuery) -> str:
    return callback.data.split('_')[-1]


def generate_tasks_kb(callback: str, tasks: list[dict[str, str]], page: int | str, field: str) -> tuple[list[list[InlineKeyboardButton]], bool]:
    kb = []
    page = int(page)
    i = page - 1
    start = i * config.entries_on_page
    end = start + config.entries_on_page
    page_tasks = tasks[start:end]
    for task in page_tasks:
        text, date = task['text'], task[field]
        if ':' in date:
            if field == 'end_date':
                time = re.sub(r'\d{4}-(\d{2})-(\d{2}) \d{2}:\d{2}', r'\2.\1', date)
            else:
                time = date.split()[-1][:-3]
            text = time + ' ' + text
        if len(text) > 40:
            text = text[:41].strip() + '…'
        kb.append([btn(text, f"view_{task['id']}")])

    additional = False
    if not page_tasks:
        additional = True
    elif len(tasks) > config.entries_on_page:
        kb.append(get_pagination_kb(callback, page, len(tasks), config.entries_on_page))
    return kb, additional


def get_navigation(date: datetime, days_delta: int, callback: str) -> list[InlineKeyboardButton]:
    row = []
    delta = timedelta(days=days_delta)
    for btn_text in ['◀️ Назад', '▶️ Далее']:
        date_result = date - delta if '◀️' in btn_text else date + delta
        db_format = date_result.strftime('%Y-%m-%d')
        row.append(btn(btn_text, f'{callback}_{db_format}'))
    return row


def get_page(date_str: str, user_id: int, page: int | str) -> tuple[str, InlineKeyboardMarkup]:
    query = f'''
        select * from tasks
        where notification_date like '{date_str}%' and end_date is NULL and user_id = ?
        order by
            case when notification_date not like '%:%' THEN 1 ELSE 0 END,
            notification_date,
            creation_date desc
    '''
    tasks = db.execute_query(query, user_id)
    kb, additional = generate_tasks_kb(date_str, tasks, page, 'notification_date')
    date = datetime.strptime(date_str, '%Y-%m-%d')
    natural_day = format_date(date)
    text = texts.get('tasks').format(natural_day)
    if 'сегодня' in natural_day:
        text = texts.get('today_emoji') + text[2:]
        tomorrow = to_db_str(get_tomorrow()).split()[0]
        kb.append([btn('Задачи на завтра ▶\uFE0F', f'list_{tomorrow}')])
    else:
        kb.append(get_navigation(date, 1, 'list'))
    if additional:
        text += '\n\n' + texts.get('no_tasks')
    return text, markup(kb)


async def get_today_tasks(user_id: int):
    date_str = to_db_str(now_date()).split()[0]
    return get_page(date_str, user_id, 1)


@router.message(Command('list'))
async def view_tasks(message: Message):
    text, kb = await get_today_tasks(message.from_user.id)
    await message.answer(text=text, reply_markup=kb, parse_mode='HTML')
    await message.delete()


@router.callback_query(F.data.startswith('view'))
async def view_task(callback: CallbackQuery):
    task_id = get_id(callback)
    task = db.execute_query('select * from tasks where id = ? order by notification_date', task_id)[0]
    text = f'{task['text']}\n\n🕓 Создано: {reformat_db_str(task['creation_date'])}'
    if task['end_date']:
        text += f'\n✅ Выполнено: {reformat_db_str(task['end_date'])}'
    await callback.message.edit_text(text=text, reply_markup=get_back_kb(task))


@router.callback_query(F.data.startswith('list'))
async def view_tasks_list(callback: CallbackQuery):
    date_str = get_id(callback)
    text, kb = get_page(date_str, callback.from_user.id, 1)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data.startswith('page'))
async def view_tasks_list(callback: CallbackQuery):
    page, date_str = callback.data.split('_')[1:3]
    if callback.data.endswith('week'):
        text, kb = get_completed_tasks(date_str, callback.from_user.id, page)
    else:
        text, kb = get_page(date_str, callback.from_user.id, page)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data == 'null')
async def null_cb(callback: CallbackQuery):
    await callback.answer('😢 Нет значений!')


def get_completed_tasks(date: datetime | str, user_id: int, page: int | str) -> tuple[str, InlineKeyboardMarkup]:
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    mon, sun = get_week(date)
    sun = sun + timedelta(days=1)
    query = f'''
        select * from tasks
        where end_date is not NULL and end_date between '{mon.strftime('%Y-%m-%d')}' and '{sun.strftime('%Y-%m-%d')}' and user_id = ?
        order by end_date
    '''
    tasks = db.execute_query(query, user_id)
    date_str = to_db_str(date).split()[0]
    kb, additional = generate_tasks_kb(date_str + '_week', tasks, page, 'end_date')
    kb.append(get_navigation(mon, 7, 'completed'))
    text = texts.get('completed_tasks').format(get_weekday(mon).split(',')[0], get_weekday(sun).split(',')[0])
    if additional:
        text += '\n\n' + texts.get('no_completed_tasks')
    return text, markup(kb)


@router.message(Command('completed'))
async def view_completed_tasks(message: Message):
    text, kb = get_completed_tasks(now_date(), message.from_user.id, 1)
    await message.answer(text=text, parse_mode='HTML', reply_markup=kb)
    await message.delete()


@router.callback_query(F.data.startswith('completed'))
async def view_completed(callback: CallbackQuery):
    text, kb = get_completed_tasks(get_id(callback), callback.from_user.id, 1)
    await callback.message.edit_text(text=text, parse_mode='HTML', reply_markup=kb)
