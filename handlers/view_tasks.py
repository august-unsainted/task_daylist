from datetime import timedelta, datetime
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot_config import *
from utils.time import now_date, weekday_date, to_str, to_db_str, reformat_db_str

router = Router()


@router.message(Command('list'))
async def view_tasks(message: Message):
    now = now_date()
    answer = texts.get('today_tasks').format(weekday_date(now))
    query = f"select * from tasks where notification_date like '{to_db_str(now).split()[0]}%' and user_id = ?"
    tasks = db.execute_query(query, message.from_user.id)
    kb = []
    for task in tasks:
        text = task['text']
        date = task['notification_date']
        if ':' in date:
            text = date.split()[-1] + ' ' + text
        if len(text) > 30:
            text = text[:31] + '…'
        kb.append([InlineKeyboardButton(text=text, callback_data=f"view_{task['id']}")])
    await message.answer(text=answer, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith('view'))
async def view_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[-1]
    task = db.execute_query('select * from tasks where id = ? order by notification_date', task_id)[0]
    text = f'{task['text']}\n\n🕓 Создано: {reformat_db_str(task['creation_date'])}'
    if task['end_date']:
        text += f'\n✅ Выполнено: {reformat_db_str(task['end_date'])}'
    kb = config.edit_keyboard(task_id, 'view')
    kb.inline_keyboard.append([InlineKeyboardButton(text='◀️ Назад', callback_data='list')])
    await callback.message.edit_text(text=text, reply_markup=kb)
