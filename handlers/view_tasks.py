from datetime import datetime, timedelta

import humanize
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from humanize import naturalday

from bot_config import *
from utils.keyboards import get_pagination_kb, btn, markup
from utils.time import now_date, get_weekday, to_str, to_db_str, reformat_db_str, get_tomorrow, get_week

_t = humanize.i18n.activate("ru_RU")

router = Router()


def generate_tasks_kb(callback: str, tasks: list[dict[str, str]], page: int) -> tuple[list[list[InlineKeyboardButton]], bool]:
    kb = []
    i = page - 1
    start = i * config.entries_on_page
    end = start + config.entries_on_page
    page_tasks = tasks[start:end]
    for task in page_tasks:
        text = task['text']
        date = task['notification_date']
        if ':' in date:
            text = date.split()[-1] + ' ' + text
        if len(text) > 30:
            text = text[:31] + '…'
        kb.append([btn(text, f"view_{task['id']}")])

    additional = False
    if not page_tasks:
        additional = True
    elif len(tasks) > config.entries_on_page:
        kb.insert(-1, get_pagination_kb(callback, page, len(tasks), config.entries_on_page))
    return kb, additional


def get_page(date_str: str, user_id: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
    query = f'''
    select * from tasks
    where notification_date like '{date_str}%' and end_date is NULL and user_id = ?
    order by notification_date
    '''
    tasks = db.execute_query(query, user_id)
    kb, additional = generate_tasks_kb(date_str, tasks, page)

    date = datetime.strptime(date_str, '%Y-%m-%d')
    natural_day = naturalday(date)
    weekday = get_weekday(date)
    if natural_day == 'сегодня':
        text = texts.get('today_tasks').format(weekday)
        tomorrow = to_db_str(get_tomorrow()).split()[0]
        kb.append([btn('Задачи на завтра ▶\uFE0F', f'list_{tomorrow}')])
    else:
        if natural_day != date.strftime('%b %d'):
            weekday = f'{natural_day} ({weekday})'
        text = texts.get('tasks').format(weekday)
        row = []
        for symb in ['◀️', '▶️']:
            is_prev = symb == '◀️'
            delta = timedelta(days=1)
            date_result = date - delta if is_prev else date + delta
            user_format = date_result.strftime('%d.%m')
            db_format = date_result.strftime('%Y-%m-%d')
            btn_text = f'{symb} {user_format}' if is_prev else f'{user_format} {symb}'
            row.append(btn(btn_text, f'list_{db_format}'))
        kb.append(row)

    if additional:
        text += '\n\n' + texts.get('no_tasks')
    return text, markup(kb)


@router.message(Command('list'))
async def view_tasks(message: Message):
    date_str = to_db_str(now_date()).split()[0]
    text, kb = get_page(date_str, message.from_user.id, 1)
    await message.answer(text=text, parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data.startswith('view'))
async def view_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    task = db.execute_query('select * from tasks where id = ? order by notification_date', task_id)[0]
    text = f'{task['text']}\n\n🕓 Создано: {reformat_db_str(task['creation_date'])}'
    if task['end_date']:
        text += f'\n✅ Выполнено: {reformat_db_str(task['end_date'])}'
    kb = config.edit_keyboard(task_id, 'view')
    date_info = task['notification_date'].split()[0]
    kb.inline_keyboard.append([btn('◀️ Назад', f'list_{date_info}')])
    await callback.message.edit_text(text=text, reply_markup=kb)


@router.callback_query(F.data.startswith('list'))
async def view_tasks_list(callback: CallbackQuery):
    date_str = callback.data.split('_')[-1]
    text, kb = get_page(date_str, callback.from_user.id, 1)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data.startswith('page'))
async def view_tasks_list(callback: CallbackQuery):
    page, date_str = callback.data.split('_')[1:]
    text, kb = get_page(date_str, callback.from_user.id, int(page))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(F.data == 'null')
async def null_cb(callback: CallbackQuery):
    await callback.answer('😢 Нет значений!')


def get_completed_tasks(date: datetime, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    mon, sun = get_week(date)
    query = f'''
            select * from tasks
            where notification_date between '{mon.strftime('%Y-%m-%d')}' and '{sun.strftime('%Y-%m-%d')}' and end_date is not NULL and user_id = ?
            order by end_date desc
        '''
    tasks = db.execute_query(query, user_id)
    date_str = to_db_str(now_date()).split()[0]
    kb, additional = generate_tasks_kb(date_str + '_week', tasks, 1)
    row = []
    for symb in ['◀️', '▶️']:
        delta = timedelta(days=7)
        is_prev = symb == '◀️'
        date_result = mon - delta if is_prev else mon + delta
        result_mon, result_sun = get_week(date_result)
        user_format = f'{result_mon.strftime('%d.%m')}-{result_sun.strftime('%d.%m')}'
        db_format = date_result.strftime('%Y-%m-%d')
        btn_text = f'{symb} {user_format}' if is_prev else f'{user_format} {symb}'
        row.append(btn(btn_text, f'completed_{db_format}'))
    kb.append(row)
    text = texts.get('completed_tasks').format(get_weekday(mon).split(',')[0], get_weekday(sun).split(',')[0])
    if additional:
        text += '\n\n' + texts.get('no_completed_tasks')
    return text, markup(kb)


@router.message(Command('completed'))
async def view_completed_tasks(message: Message):
    text, kb = get_completed_tasks(now_date(), message.from_user.id)
    await message.answer(text=text, parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data.startswith('completed'))
async def view_completed(callback: CallbackQuery):
    date = datetime.strptime(callback.data.split('_')[-1], '%Y-%m-%d')
    text, kb = get_completed_tasks(date, callback.from_user.id)
    await callback.message.edit_text(text=text, parse_mode='HTML', reply_markup=kb)
