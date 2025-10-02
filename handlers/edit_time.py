import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot_config import *
from utils.schedule import schedule_regular
from utils.time import TIME_REG, pad

router = Router()


class TimeStates(StatesGroup):
    time = State()


@router.message(Command('time'))
async def edit_time(message: Message, state: FSMContext):
    answer = await message.answer('Напиши время в формате 10:00')
    await state.update_data(message=answer.message_id)
    await state.set_state(TimeStates.time)


@router.message(TimeStates.time)
async def set_time(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text.strip()
    await message.delete()
    if re.fullmatch(TIME_REG, text):
        await schedule_regular(message.from_user.id, pad(text, ':'))
        answer = texts.get('edit_time')
        await state.clear()
    else:
        answer = texts.get('error')
        await state.set_state(TimeStates.time)
    await message.bot.edit_message_text(chat_id=message.from_user.id, message_id=data['message'],
                                        text=answer.format(text), parse_mode='HTML')


