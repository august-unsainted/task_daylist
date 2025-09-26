from datetime import datetime

import humanize
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from humanize import naturalday

from bot_config import *
from utils.time import now_date, weekday_date, to_str, to_db_str, reformat_db_str, get_tomorrow

_t = humanize.i18n.activate("ru_RU")

router = Router()


def get_tasks_kb(date_str: str, user_id: int) -> InlineKeyboardMarkup:
    query = f"select * from tasks where notification_date like '{date_str}%' and user_id = ?"
    tasks = db.execute_query(query, user_id)
    kb = []
    for task in tasks:
        text = task['text']
        date = task['notification_date']
        if ':' in date:
            text = date.split()[-1] + ' ' + text
        if len(text) > 30:
            text = text[:31] + '…'
        kb.append([InlineKeyboardButton(text=text, callback_data=f"view_{task['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(Command('list'))
async def view_tasks(message: Message):
    now = now_date()
    answer = texts.get('today_tasks').format(weekday_date(now))
    kb = get_tasks_kb(to_db_str(now).split()[0], message.from_user.id)
    tomorrow = to_db_str(get_tomorrow()).split()[0]
    kb.inline_keyboard.append([InlineKeyboardButton(text='Задачи на завтра ▶\uFE0F',
                                                    callback_data=f'list_{tomorrow}')])
    await message.answer(text=answer, parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data.startswith('view'))
async def view_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    task = db.execute_query('select * from tasks where id = ? order by notification_date', task_id)[0]
    text = f'{task['text']}\n\n🕓 Создано: {reformat_db_str(task['creation_date'])}'
    if task['end_date']:
        text += f'\n✅ Выполнено: {reformat_db_str(task['end_date'])}'
    kb = config.edit_keyboard(task_id, 'view')
    date_info = task['notification_date'].split()[0]
    kb.inline_keyboard.append([InlineKeyboardButton(text='◀️ Назад', callback_data=f'list_{date_info}')])
    await callback.message.edit_text(text=text, reply_markup=kb)


@router.callback_query(F.data.startswith('list'))
async def view_tasks_list(callback: CallbackQuery):
    date_str = callback.data.split('_')[-1]
    date = datetime.strptime(date_str, '%Y-%m-%d')
    natural_day = naturalday(date)
    weekday = weekday_date(date)
    kb = get_tasks_kb(date_str, callback.from_user.id)
    if natural_day == 'сегодня':
        text = texts.get('today_tasks').format(weekday)
    else:
        if natural_day != date:
            weekday = f'{natural_day} ({weekday})'
        text = texts.get('tasks').format(weekday)
    tomorrow = to_db_str(get_tomorrow()).split()[0]
    kb.inline_keyboard.append([InlineKeyboardButton(text='Задачи на завтра ▶\uFE0F',
                                                    callback_data=f'list_{tomorrow}')])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
