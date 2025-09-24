from datetime import timedelta
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot_config import *
from utils.time import now_date, weekday_date, to_str

router = Router()


@router.message(Command('tasks'))
async def view_tasks(message: Message):
    now = now_date()
    text = texts.get('today_tasks').format(weekday_date(now))
    query = f"select * from tasks where notification_date like '{now.strftime("%d.%m.%y")}%'"
    tasks = db.execute_query(query)
    kb = []
    for task in tasks:
        kb.append([InlineKeyboardButton(text=task['text'][:10], callback_data=f"view_{task['id']}")])
    await message.answer(text=text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
