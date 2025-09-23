from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot_config import *
from utils.time import now, convert_to_stamp

router = Router()


class EditStates(StatesGroup):
    text = State()


def get_add_args(text: str, entry_id: int, query: str) -> dict:
    if ' [' not in text:
        return {'text': 'Неправильный формат'}
    task, date = text.strip().split(' [')
    date = date[:-1]
    day, time = date.split(', ')
    answer_text = texts.get('new').format(day, task, time)
    task_id = db.execute_query(query, task, now(), convert_to_stamp(date), entry_id)
    kb = config.edit_keyboard(task_id, 'new')
    return {'text': answer_text, 'parse_mode': 'HTML', 'reply_markup': kb}


@router.callback_query(F.data.startswith('delete'))
async def delete_task(callback: CallbackQuery):
    task_id = callback.data.split('_')[0]
    db.execute_query('delete from tasks where id = ?', task_id)
    await callback.message.edit_text(texts.get('delete'))


@router.callback_query(F.data.startswith('edit'))
async def set_edit_task(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введите текст')
    task_id = callback.data.split('_')[-1]
    await state.update_data(message=callback.message.message_id, task=task_id)
    await state.set_state(EditStates.text)


@router.message(EditStates.text)
async def edit_task(message: Message, state: FSMContext):
    data = await state.get_data()
    query = 'update tasks set text = ?, creation_date = ?, notification_date = ? where id = ?'
    args = get_add_args(message.text, data['task'], query)
    await message.delete()
    await message.bot.edit_message_text(message_id=data.get('message'), chat_id=message.chat.id,
                                        **args)


@router.message()
async def add_task(message: Message):
    query = 'insert into tasks (text, creation_date, notification_date, user_id) values (?, ?, ?, ?)'
    args = get_add_args(message.text, message.from_user.id, query)
    await message.answer(**args)
